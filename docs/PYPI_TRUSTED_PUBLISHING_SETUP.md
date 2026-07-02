# sourcea-boot — PyPI Trusted Publishing Setup (Phase 0b)

**Saved:** 2026-07-01T24:15:00Z  
**Status:** prep_only — **do not publish** until founder confirms PyPI project ownership  
**Package:** `sourcea-boot` · **Public repo:** `https://github.com/kazemnezhadsina144-dot/sourcea-boot`  
**Workflow:** `.github/workflows/publish-pypi-v1.yml`

---

## What this enables

GitHub Actions uploads `sourcea-boot` to PyPI using **OIDC trusted publishing** — no long-lived `PYPI_API_TOKEN` stored in GitHub secrets.

---

## Founder checklist (PyPI side)

Complete these steps **before** creating a GitHub Release or running the publish workflow.

### 1. Create or claim the PyPI project

1. Sign in at [https://pypi.org](https://pypi.org) with the SourceA PyPI account.
2. If `sourcea-boot` does not exist yet, create the project (or reserve the name per PyPI policy).
3. Confirm you are **Owner** or **Maintainer** on `https://pypi.org/project/sourcea-boot/`.

### 2. Add Trusted Publisher (exact settings)

In PyPI → **Your projects** → **sourcea-boot** → **Publishing** → **Add a new pending publisher**:

| Field | Value |
|-------|--------|
| **PyPI Project Name** | `sourcea-boot` |
| **Owner** | `kazemnezhadsina144-dot` |
| **Repository name** | `sourcea-boot` |
| **Workflow name** | `publish-pypi-v1.yml` |
| **Environment name** | `pypi` *(optional but recommended — matches workflow `environment: pypi`)* |

Save. PyPI shows the publisher as **pending** until the first successful upload from that workflow.

### 3. GitHub environment (recommended)

In `kazemnezhadsina144-dot/sourcea-boot` → **Settings** → **Environments** → **New environment**:

- Name: `pypi`
- **Deployment branches:** restrict to `main` only (optional hardening)
- **No secrets required** for trusted publishing

### 4. Export workflow to public repo

From SourceA monorepo:

```bash
python3 scripts/publish_sourcea_boot_public_v1.py --push-existing --json
```

This copies `.github/workflows/publish-pypi-v1.yml` and `build-check-pypi-v1.yml` into the public repo.

---

## How publish runs (after setup)

### Option A — GitHub Release (preferred)

1. Bump version in `pyproject.toml` (semver).
2. Tag and create a **GitHub Release** (published, not draft).
3. Workflow `publish-pypi-v1.yml` runs automatically: build → `twine check` → PyPI upload.

### Option B — Manual dispatch (founder only)

1. Actions → **publish-pypi** → **Run workflow**
2. Enter confirm string: `PUBLISH`
3. Requires trusted publisher + `pypi` environment already configured.

---

## What we deliberately omit

| Item | Reason |
|------|--------|
| `PYPI_API_TOKEN` in GitHub secrets | Replaced by OIDC trusted publishing |
| `TWINE_USERNAME` / `TWINE_PASSWORD` | Not used with `pypa/gh-action-pypi-publish` |
| Auto-publish on every push to `main` | Only release or explicit `PUBLISH` dispatch |

---

## Post-publish (separate founder pass)

After `pip install sourcea-boot` resolves on PyPI:

1. Update public README — uncomment `pip install sourcea-boot` as primary install path.
2. Update `sourcea.app/eval` + trust-signals only when live.
3. Run `bash scripts/validate-sourcea-boot-v1.sh` in monorepo.

Until then, README keeps **clone + editable install** as the honest current method.

---

## Verify locally (no publish)

```bash
cd packages/sourcea-boot
python3 -m pip install --upgrade build twine
python3 -m build
twine check dist/*
```

---

**End LOCKED v1**
