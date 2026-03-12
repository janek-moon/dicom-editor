# Release Checklist

## 1) Version and Notes
- Update version in `pyproject.toml`.
- Update `CHANGELOG.md` (or release notes draft).
- Confirm release tag format: `vX.Y.Z`.

## 2) Quality Gate
- Run tests locally:
  - `source .venv/bin/activate`
  - `QT_QPA_PLATFORM=offscreen pytest -q`
- Validate critical flows manually:
  - Load single DICOM
  - Add -> Confirm Add
  - Update Selected
  - Save edited outputs

## 3) Build Verification
- Validate local packaging at least once before first public release:
  - `pip install pyinstaller`
  - `pyinstaller src/dicom_editor/app.py --name DicomTagEditor --windowed --paths src --collect-data dicom_editor`
- Confirm build outputs run on target OS.

## 4) GitHub Release
- Push tag:
  - `git tag vX.Y.Z`
  - `git push origin vX.Y.Z`
- Confirm workflow artifacts uploaded to GitHub Release page.
- Attach release notes with:
  - Changes
  - Known limitations
  - Upgrade notes (if any)

## 5) Post-release
- Smoke-check downloaded binaries on macOS/Windows.
- Open follow-up issues for deferred items (if any).
