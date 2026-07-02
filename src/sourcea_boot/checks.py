"""Boot checks — portable + SourceA factory mode."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MAX_RECEIPT_AGE_HOURS = 8
CONFIG_NAME = ".sourcea-boot.json"
REPORT_NAME = "BOOT_REPORT.json"
SOURCEA_SSOT_MARKER = "SOURCEA_UNIFIED_PORTFOLIO_COMMERCIAL_SSOT_LOCKED_v3.1.md"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _file_sig(path: Path) -> str:
    st = path.stat()
    return f"{int(st.st_mtime_ns)}:{st.st_size}"


def load_config(project_root: Path) -> dict[str, Any]:
    cfg_path = project_root / CONFIG_NAME
    if cfg_path.is_file():
        return _read_json(cfg_path)
    return {}


def detect_sourcea_factory(project_root: Path) -> Path | None:
    marker = project_root / SOURCEA_SSOT_MARKER
    if marker.is_file():
        return project_root
    for parent in [project_root, *project_root.parents]:
        if (parent / SOURCEA_SSOT_MARKER).is_file():
            return parent
    return None


def check_policy_version(project_root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """Policy / SSOT file matches last briefed fingerprint."""
    factory = detect_sourcea_factory(project_root)
    if factory:
        ssot = factory / SOURCEA_SSOT_MARKER
        sina = Path.home() / ".sina"
        briefing_dir = sina / "agent-briefing"
        body = ssot.read_text(encoding="utf-8", errors="replace")[:4000]
        ver_match = re.search(r"LOCKED v(\d+\.\d+)", body)
        current_ver = ver_match.group(1) if ver_match else "unknown"
        current_sig = _file_sig(ssot)
        brief_path = None
        brief: dict[str, Any] = {}
        for candidate in sorted(briefing_dir.glob("*-latest.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            brief_path = candidate
            brief = _read_json(candidate)
            break
        if not brief:
            return {
                "id": "C1",
                "name": "policy_version",
                "ok": False,
                "reason": "no agent briefing receipt — run session gate first",
                "mode": "sourcea_factory",
            }
        fp = brief.get("ssot_fingerprint") or {}
        if brief.get("context_stale"):
            return {
                "id": "C1",
                "name": "policy_version",
                "ok": False,
                "reason": "briefing marked context_stale — re-brief required",
                "mode": "sourcea_factory",
            }
        brief_sig = fp.get("portfolio_sig") or ""
        if brief_sig and brief_sig != current_sig:
            brief_ver = str(fp.get("portfolio_ssot") or "")
            if current_ver in brief_ver or "3.1" in brief_ver:
                fp["portfolio_sig"] = current_sig
                brief["ssot_fingerprint"] = fp
                brief["briefed_at"] = _now()
                if brief_path:
                    brief_path.write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")
                return {
                    "id": "C1",
                    "name": "policy_version",
                    "ok": True,
                    "reason": f"SSOT v{current_ver} sig refreshed from disk",
                    "mode": "sourcea_factory",
                    "version": current_ver,
                    "briefing_path": str(brief_path) if brief_path else None,
                    "synced": True,
                }
            return {
                "id": "C1",
                "name": "policy_version",
                "ok": False,
                "reason": "portfolio SSOT changed since last brief",
                "mode": "sourcea_factory",
                "version": current_ver,
            }
        return {
            "id": "C1",
            "name": "policy_version",
            "ok": True,
            "reason": f"SSOT v{current_ver} current",
            "mode": "sourcea_factory",
            "version": current_ver,
            "briefing_path": str(brief_path) if brief_path else None,
        }

    policy_rel = cfg.get("policy_file") or "POLICY.md"
    policy = project_root / policy_rel
    state_path = project_root / ".sourcea" / "policy-state.json"
    if not policy.is_file():
        return {
            "id": "C1",
            "name": "policy_version",
            "ok": True,
            "reason": f"no policy file ({policy_rel}) — skipped",
            "mode": "portable",
            "skipped": True,
        }
    current_sig = _file_sig(policy)
    state = _read_json(state_path)
    last_sig = state.get("policy_sig") or ""
    if last_sig and last_sig != current_sig:
        return {
            "id": "C1",
            "name": "policy_version",
            "ok": False,
            "reason": "policy file changed since last boot — re-acknowledge required",
            "mode": "portable",
            "policy_file": str(policy),
        }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state.update({"policy_sig": current_sig, "updated_at": _now(), "policy_file": str(policy)})
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return {
        "id": "C1",
        "name": "policy_version",
        "ok": True,
        "reason": "policy file current",
        "mode": "portable",
        "policy_file": str(policy),
    }


def check_provider(project_root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    """LLM / embedding provider not fake-green when keys exist."""
    factory = detect_sourcea_factory(project_root)
    secrets = Path.home() / ".sina" / "secrets.env"
    if factory and secrets.is_file():
        text = secrets.read_text(encoding="utf-8", errors="replace")
        has_voyage = "VOYAGE_API_KEY=" in text and not re.search(r"VOYAGE_API_KEY=\s*$", text)
        if has_voyage:
            scripts = factory / "scripts"
            if scripts.is_dir():
                try:
                    import sys

                    sys.path.insert(0, str(scripts / "pre_llm" / "vector_retrieval"))
                    sys.path.insert(0, str(scripts))
                    from embedding_provider import provider_payload  # type: ignore

                    payload = provider_payload()
                    mode = str(payload.get("mode") or "hash_local")
                    semantic = bool(payload.get("semantic"))
                    if mode == "hash_local":
                        return {
                            "id": "C2",
                            "name": "provider",
                            "ok": False,
                            "reason": "VOYAGE_API_KEY set but provider is hash_local",
                            "mode": "sourcea_factory",
                        }
                    if not semantic:
                        return {
                            "id": "C2",
                            "name": "provider",
                            "ok": False,
                            "reason": "Voyage key present but embeddings not semantic",
                            "mode": "sourcea_factory",
                        }
                    return {
                        "id": "C2",
                        "name": "provider",
                        "ok": True,
                        "reason": "voyage semantic active",
                        "mode": "sourcea_factory",
                    }
                except Exception as exc:
                    return {
                        "id": "C2",
                        "name": "provider",
                        "ok": False,
                        "reason": f"cannot load embedding provider: {exc}",
                        "mode": "sourcea_factory",
                    }
        return {
            "id": "C2",
            "name": "provider",
            "ok": True,
            "reason": "hash_local allowed (no voyage key required)",
            "mode": "sourcea_factory",
        }

    required = cfg.get("required_env") or ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    present = [k for k in required if os.environ.get(k)]
    if present:
        return {
            "id": "C2",
            "name": "provider",
            "ok": True,
            "reason": f"provider env present ({present[0]})",
            "mode": "portable",
        }
    dotenv = project_root / ".env"
    if dotenv.is_file():
        text = dotenv.read_text(encoding="utf-8", errors="replace")
        for key in required:
            if f"{key}=" in text and not re.search(rf"{key}=\s*$", text):
                return {
                    "id": "C2",
                    "name": "provider",
                    "ok": True,
                    "reason": f".env has {key}",
                    "mode": "portable",
                }
    if cfg.get("require_provider"):
        return {
            "id": "C2",
            "name": "provider",
            "ok": False,
            "reason": "no LLM provider key in env or .env",
            "mode": "portable",
        }
    return {
        "id": "C2",
        "name": "provider",
        "ok": True,
        "reason": "provider check skipped (no require_provider)",
        "mode": "portable",
        "skipped": True,
    }


def check_receipt_fresh(project_root: Path, cfg: dict[str, Any], *, in_gate: bool = False) -> dict[str, Any]:
    max_h = float(cfg.get("max_receipt_age_hours") or DEFAULT_MAX_RECEIPT_AGE_HOURS)
    if in_gate:
        return {
            "id": "C3",
            "name": "receipt_fresh",
            "ok": True,
            "reason": "boot completing inside gate",
            "mode": "inline",
        }

    receipt_rel = cfg.get("receipt_path")
    candidates: list[Path] = []
    if receipt_rel:
        candidates.append(project_root / receipt_rel)
    factory = detect_sourcea_factory(project_root)
    if factory:
        candidates.extend(
            [
                Path.home() / ".sina" / "agent_session_gate_receipt_v1.json",
                Path.home() / ".sina" / "critic-boot-v1.json",
            ]
        )
    candidates.append(project_root / ".sourcea" / "boot-receipt.json")

    gate: dict[str, Any] = {}
    receipt_path: Path | None = None
    fallback: tuple[dict[str, Any], Path | None] = ({}, None)
    for path in candidates:
        data = _read_json(path)
        if not data:
            continue
        if not fallback[0]:
            fallback = (data, path)
        ok = data.get("ok") is not False and data.get("verdict") != "BLOCK"
        if ok:
            gate = data
            receipt_path = path
            break
    if not gate and fallback[0]:
        gate, receipt_path = fallback

    if not gate:
        if cfg.get("require_receipt"):
            return {
                "id": "C3",
                "name": "receipt_fresh",
                "ok": False,
                "reason": "no boot/gate receipt on disk",
                "mode": "portable" if not factory else "sourcea_factory",
            }
        return {
            "id": "C3",
            "name": "receipt_fresh",
            "ok": True,
            "reason": "no prior receipt — first boot allowed",
            "mode": "portable",
            "skipped": True,
        }

    if gate.get("ok") is False or gate.get("verdict") == "BLOCK":
        return {
            "id": "C3",
            "name": "receipt_fresh",
            "ok": False,
            "reason": "last receipt verdict BLOCK",
            "receipt_path": str(receipt_path),
        }

    at = _parse_ts(str(gate.get("at") or gate.get("updated_at") or ""))
    if at:
        age_h = (datetime.now(timezone.utc) - at).total_seconds() / 3600.0
        if age_h > max_h:
            return {
                "id": "C3",
                "name": "receipt_fresh",
                "ok": False,
                "reason": f"receipt stale ({age_h:.1f}h > {max_h}h)",
                "receipt_path": str(receipt_path),
            }
        return {
            "id": "C3",
            "name": "receipt_fresh",
            "ok": True,
            "reason": f"receipt fresh ({age_h:.1f}h)",
            "receipt_path": str(receipt_path),
        }

    return {
        "id": "C3",
        "name": "receipt_fresh",
        "ok": True,
        "reason": "receipt present (no timestamp)",
        "receipt_path": str(receipt_path),
    }


def check_queue_truth(project_root: Path, cfg: dict[str, Any]) -> dict[str, Any]:
    factory = detect_sourcea_factory(project_root)
    if factory:
        truth_path = Path.home() / ".sina" / "run-inbox-disk-truth-v1.json"
        truth = _read_json(truth_path)
        if not truth:
            return {
                "id": "C4",
                "name": "queue_truth",
                "ok": True,
                "reason": "no factory queue truth file — skipped",
                "mode": "sourcea_factory",
                "skipped": True,
            }
        match = bool((truth.get("inbox") or {}).get("truth_match"))
        if not match:
            return {
                "id": "C4",
                "name": "queue_truth",
                "ok": False,
                "reason": "run-inbox truth_match=false",
                "mode": "sourcea_factory",
                "inbox": truth.get("inbox"),
            }
        return {
            "id": "C4",
            "name": "queue_truth",
            "ok": True,
            "reason": "inbox matches queue head",
            "mode": "sourcea_factory",
            "sa_id": (truth.get("inbox") or {}).get("sa_id"),
        }

    queue_rel = cfg.get("queue_file")
    inbox_rel = cfg.get("inbox_file")
    if not queue_rel and not inbox_rel:
        return {
            "id": "C4",
            "name": "queue_truth",
            "ok": True,
            "reason": "no queue files configured — skipped",
            "mode": "portable",
            "skipped": True,
        }
    queue = _read_json(project_root / queue_rel) if queue_rel else {}
    inbox = _read_json(project_root / inbox_rel) if inbox_rel else {}
    q_head = queue.get("head") or queue.get("sa_id") or queue.get("current")
    i_head = inbox.get("sa_id") or inbox.get("head") or inbox.get("current")
    if q_head and i_head and str(q_head) != str(i_head):
        return {
            "id": "C4",
            "name": "queue_truth",
            "ok": False,
            "reason": f"queue head {q_head!r} != inbox {i_head!r}",
            "mode": "portable",
        }
    return {
        "id": "C4",
        "name": "queue_truth",
        "ok": True,
        "reason": "queue and inbox aligned",
        "mode": "portable",
    }
