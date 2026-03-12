from pathlib import Path
import json

from dicom_editor.tag_registry import TagRegistry


def test_registry_allows_standard_tag():
    reg = TagRegistry()
    assert reg.is_editable(0x00100010)
    meta = reg.get_meta(0x00100010)
    assert meta is not None
    assert meta.vr == "PN"


def test_registry_blocks_unknown_private_like_tag():
    reg = TagRegistry()
    assert not reg.is_editable(0x77771010)


def test_registry_remote_update(tmp_path: Path):
    base_file = tmp_path / "base.json"
    base_file.write_text(
        json.dumps([{"tag": "00100010", "name": "PatientName", "vr": "PN", "retired": False}]),
        encoding="utf-8",
    )

    remote_file = tmp_path / "remote.json"
    remote_file.write_text(
        json.dumps([{"tag": "00100020", "name": "PatientID", "vr": "LO", "retired": False}]),
        encoding="utf-8",
    )

    reg = TagRegistry(allowlist_path=base_file, remote_url="")
    assert reg.is_editable(0x00100010)
    assert not reg.is_editable(0x00100020)

    ok = reg.try_update_from_remote(remote_file.as_uri())
    assert ok
    assert reg.is_editable(0x00100020)
