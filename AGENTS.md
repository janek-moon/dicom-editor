# AGENTS.md

## Project Goal
- Build a desktop DICOM tag editor with GUI.
- Tech stack: Python, PySide6, pydicom.

## Core Functional Requirements
- Load DICOM file or folder.
- Show tags in table with columns:
  - Path
  - Tag
  - Name
  - VR
  - Value
- Support tag operations:
  - Add
  - Update
  - Remove
- Save edited output as new files (preserve originals).

## Scope and Data Rules
- Editing is constrained to standard tag allowlist based on Innolitics scope.
- Policy for allowlist:
  - Static embedded snapshot in repo.
  - If internet is available at runtime, fetch latest snapshot and refresh cache.
- Current implementation includes local data files under `src/dicom_editor/data/`.

## Batch and Grouping
- Folder mode groups files by set:
  - `StudyInstanceUID + SeriesInstanceUID`
- Apply same edit operations to all files in selected set on save.

## Sequence/Nested Tag Support
- Support nested path editing syntax:
  - Example: `00400275[0].00100010`
- Path handling expectations:
  - Path is auto-selected from selected row when applicable.
  - Path candidates filtered by selected tag.

## Add vs Update UX (Must Stay Separated)
- Update:
  - Works only for selected existing row.
  - Button label: `Update Selected`.
  - Disabled when no row is selected.
- Add:
  - Two-step flow only:
    1. Click `추가하기`
    2. Enter fields and click `Add`
  - Add must not depend on selected row context by default.
  - Default add target is root-level path for selected tag unless user explicitly provides matching nested path.

## Select/Autocomplete UX
- Path and Value inputs use selectable controls (editable combo box).
- Tag input uses select + autocomplete.
- Tag display format in combo:
  - `Description (GGGG,EEEE)` (description first)
- When Tag changes:
  - Path candidates must refresh for that tag.
  - Value candidates must refresh for that tag.
- Value options should include:
  - Existing values found in current data
  - Preset values (where defined), merged not replaced

## Approval Status Specific Behavior
- Tag `Approval Status (300E,0002)` is supported.
- Value presets include:
  - `APPROVED`
  - `UNAPPROVED`
  - `REJECTED`
- Conditional required fields when Approval Status is `APPROVED` or `REJECTED`:
  - `Review Date (300E,0004)`
  - `Review Time (300E,0005)`
  - `Reviewer Name (300E,0008)`

## Module Required-Tag Autofill
- On Add, auto-add required tags for related module(s) based on Innolitics-derived module data.
- Current policy:
  - Auto-fill Type 1/2 required attributes by module mapping.
  - Includes selected conditional rule handling for Approval module case above.
- Log auto-added tag count and module names in UI log.

## Table and Interaction
- Table sorting enabled by default.
- Keep update/add/remove operations reflected immediately in preview table.

## Visual Design
- UI theme: dark mode.
- Maintain readable control sizes and spacing.
- Combo/dropdown arrow visibility must remain clear in dark theme.

## Safety/Validation
- Block add/update for tags outside allowlist.
- Warn before deleting critical tags (e.g., SOP/Study/Series UID, Patient ID).

## Testing Expectations
- Keep automated tests passing.
- Prefer adding tests for:
  - Add/Update separation behavior
  - Tag->Path->Value selection behavior
  - Approval conditional autofill behavior
  - Module autofill behavior
