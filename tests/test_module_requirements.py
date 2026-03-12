from pathlib import Path
import json

from pydicom.dataset import Dataset

from dicom_editor.module_requirements import ModuleRequirementsEngine
from dicom_editor.tag_registry import TagRegistry


def test_suggest_required_ops_with_custom_requirements(tmp_path: Path):
    req = {
        "module_names": {"mod-a": "Module A"},
        "module_required_tags": {"mod-a": ["00100020", "00080020"]},
        "tag_to_modules": {"300E0002": ["mod-a"]},
        "ciod_to_modules": {},
        "sop_to_ciod": {},
    }
    req_path = tmp_path / "req.json"
    req_path.write_text(json.dumps(req), encoding="utf-8")

    reg = TagRegistry()
    eng = ModuleRequirementsEngine(registry=reg, requirements_path=req_path)

    ds = Dataset()
    ds.add_new(0x300E0002, "CS", "APPROVED")

    result = eng.suggest_required_ops(ds, 0x300E0002)
    tags = {op.tag for op in result.ops}
    assert 0x00100020 in tags
    assert 0x00080020 in tags
    assert "Module A" in result.modules


def test_approval_status_adds_conditional_review_fields():
    reg = TagRegistry()
    eng = ModuleRequirementsEngine(registry=reg)

    ds = Dataset()
    ds.add_new(0x300E0002, "CS", "APPROVED")

    result = eng.suggest_required_ops(ds, 0x300E0002)
    tags = {op.tag for op in result.ops}
    assert 0x300E0004 in tags  # Review Date
    assert 0x300E0005 in tags  # Review Time
    assert 0x300E0008 in tags  # Reviewer Name
