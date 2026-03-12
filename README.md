# DICOM Tag Editor

Desktop DICOM tag editor built with Python, PySide6, and pydicom.

## Demo Video

<!-- Use one of the blocks below -->

<!-- Local video (full width) -->
<!--
<video width="100%" controls>
  <source src="./assets/demo.mp4" type="video/mp4" />
</video>
-->

<!-- YouTube embed (full width) -->
<!--
<iframe
  width="100%"
  height="480"
  src="https://www.youtube.com/embed/YOUR_VIDEO_ID"
  title="Demo Video"
  frameborder="0"
  allowfullscreen>
</iframe>
-->

## Minimum Requirements

- OS:
  - macOS 13+ (tested)
  - Windows 10/11 (expected)
- Python: 3.10 or newer
- RAM: 4 GB minimum (8 GB recommended)
- Disk:
  - 500 MB free for app + dependencies
  - Additional space for edited DICOM outputs
- Network:
  - Optional (only needed when using remote allowlist refresh via `DICOM_ALLOWLIST_URL`)

## Highlights

- Load a single DICOM file or scan a folder.
- View tags as: `Path`, `Tag`, `Name`, `VR`, `Value`.
- Edit operations:
  - `Start Add` -> fill fields -> `Confirm Add`
  - `Update Selected` (works only for a selected existing row)
  - `Remove Selected`
- Nested sequence path support (example: `00400275[0].00100010`).
- Batch apply edits to a set grouped by:
  - `StudyInstanceUID + SeriesInstanceUID`
- Save to new files (`edited_<original_name>`) while preserving originals.
- Dark theme UI with sortable tag table.

## DICOM Rules

- Standard-tag editing is constrained by an Innolitics-scoped allowlist.
- Embedded static allowlist snapshot is included:
  - `src/dicom_editor/data/innolitics_allowlist.json`
- Optional runtime refresh from remote snapshot:
  - Set `DICOM_ALLOWLIST_URL` to a JSON URL
  - Successful refresh is cached at `~/.dicom-tag-editor/allowlist-cache.json`

## Required Tag Autofill

When adding a tag, the app can auto-add required tags by Innolitics module rules.

- Base behavior:
  - Module Type 1/2 required tags are auto-added (broad coverage via Innolitics-derived module mapping).
- Conditional behavior:
  - Generic 1C/2C condition parsing is **not** fully implemented yet.
  - Currently implemented conditional case:
  - If `Approval Status (300E,0002)` is `APPROVED` or `REJECTED`, auto-add:
    - `Review Date (300E,0004)`
    - `Review Time (300E,0005)`
    - `Reviewer Name (300E,0008)`

## Install and Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m dicom_editor.app
```

With remote allowlist refresh:

```bash
export DICOM_ALLOWLIST_URL="https://your-host/latest_allowlist.json"
python -m dicom_editor.app
```

## Tests

```bash
pip install -e .[dev]
pytest -q
```

## License

MIT. See [LICENSE](./LICENSE).
