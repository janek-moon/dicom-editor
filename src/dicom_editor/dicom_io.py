from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import pydicom
from pydicom.dataset import Dataset


@dataclass(frozen=True)
class DicomFileRecord:
    path: Path
    study_uid: str
    series_uid: str


def read_dataset(path: Path) -> Dataset:
    return pydicom.dcmread(str(path), force=True)


def read_for_index(path: Path) -> DicomFileRecord:
    ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
    study_uid = str(getattr(ds, "StudyInstanceUID", "UNKNOWN_STUDY"))
    series_uid = str(getattr(ds, "SeriesInstanceUID", "UNKNOWN_SERIES"))
    return DicomFileRecord(path=path, study_uid=study_uid, series_uid=series_uid)


def discover_dicom_files(folder: Path) -> Tuple[List[DicomFileRecord], List[Tuple[Path, str]]]:
    ok: List[DicomFileRecord] = []
    failed: List[Tuple[Path, str]] = []
    for p in sorted(folder.rglob("*")):
        if not p.is_file():
            continue
        try:
            ok.append(read_for_index(p))
        except Exception as exc:
            failed.append((p, str(exc)))
    return ok, failed


def group_by_set(records: List[DicomFileRecord]) -> Dict[str, List[Path]]:
    groups: Dict[str, List[Path]] = {}
    for r in records:
        key = f"{r.study_uid}|{r.series_uid}"
        groups.setdefault(key, []).append(r.path)
    return groups


def write_dataset(ds: Dataset, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ds.save_as(str(output_path), write_like_original=False)
