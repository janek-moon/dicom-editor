from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
import pytest

from dicom_editor.edit_ops import EditOperation, EditOpsEngine
from dicom_editor.tag_registry import TagRegistry


def test_update_and_add_and_remove():
    engine = EditOpsEngine(TagRegistry())
    ds = Dataset()
    ds.add_new(0x00100010, "PN", "Old Name")

    ops = [
        EditOperation(op="update", tag=0x00100010, value="New Name"),
        EditOperation(op="add", tag=0x00100020, value="PAT-001"),
        EditOperation(op="remove", tag=0x00100020),
    ]

    engine.apply_all(ds, ops)
    assert str(ds[0x00100010].value) == "New Name"
    assert 0x00100020 not in ds


def test_sequence_path_update():
    engine = EditOpsEngine(TagRegistry())
    ds = Dataset()

    item = Dataset()
    item.add_new(0x00100010, "PN", "Before")
    ds.add_new(0x00400275, "SQ", Sequence([item]))

    op = EditOperation(
        op="update",
        tag=0x00100010,
        path="00400275[0].00100010",
        value="After",
    )

    engine.apply_one(ds, op)
    assert str(ds[0x00400275].value[0][0x00100010].value) == "After"


def test_reject_non_allowlist_add():
    engine = EditOpsEngine(TagRegistry())
    ds = Dataset()

    with pytest.raises(ValueError):
        engine.apply_one(ds, EditOperation(op="add", tag=0x77771010, vr="LO", value="X"))
