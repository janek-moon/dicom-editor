from pathlib import Path

from dicom_editor.dicom_io import DicomFileRecord, group_by_set


def test_group_by_set():
    records = [
        DicomFileRecord(path=Path("a.dcm"), study_uid="S1", series_uid="R1"),
        DicomFileRecord(path=Path("b.dcm"), study_uid="S1", series_uid="R1"),
        DicomFileRecord(path=Path("c.dcm"), study_uid="S1", series_uid="R2"),
    ]

    grouped = group_by_set(records)
    assert len(grouped) == 2
    assert len(grouped["S1|R1"]) == 2
    assert len(grouped["S1|R2"]) == 1
