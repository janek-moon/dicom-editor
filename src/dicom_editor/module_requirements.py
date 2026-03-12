from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, List

from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
from pydicom.tag import Tag
from pydicom.uid import generate_uid

from .edit_ops import EditOperation
from .tag_registry import TagRegistry


MODULE_REQUIREMENTS_PATH = Path(__file__).with_name("data") / "module_requirements.json"
CONDITIONAL_REQUIRED_BY_TRIGGER_VALUE = {
    # Approval Status: if APPROVED/REJECTED then review date/time/reviewer are required (Type 2C).
    "300E0002": {
        "APPROVED": ["300E0004", "300E0005", "300E0008"],
        "REJECTED": ["300E0004", "300E0005", "300E0008"],
    }
}


@dataclass(frozen=True)
class AutoAddResult:
    ops: List[EditOperation]
    modules: List[str]


class ModuleRequirementsEngine:
    def __init__(self, registry: TagRegistry, requirements_path: Path = MODULE_REQUIREMENTS_PATH) -> None:
        self.registry = registry
        self.module_names: Dict[str, str] = {}
        self.module_required_tags: Dict[str, List[str]] = {}
        self.tag_to_modules: Dict[str, List[str]] = {}
        self.ciod_to_modules: Dict[str, List[str]] = {}
        self.sop_to_ciod: Dict[str, str] = {}
        if requirements_path.exists():
            data = json.loads(requirements_path.read_text(encoding="utf-8"))
            self.module_names = data.get("module_names", {})
            self.module_required_tags = data.get("module_required_tags", {})
            self.tag_to_modules = data.get("tag_to_modules", {})
            self.ciod_to_modules = data.get("ciod_to_modules", {})
            self.sop_to_ciod = data.get("sop_to_ciod", {})

    def _default_value_for_vr(self, vr: str) -> object:
        now = datetime.now()
        if vr in {"LO", "SH", "ST", "LT", "UT", "PN", "CS", "AE"}:
            return "AUTO"
        if vr == "DA":
            return now.strftime("%Y%m%d")
        if vr == "TM":
            return now.strftime("%H%M%S")
        if vr == "DT":
            return now.strftime("%Y%m%d%H%M%S")
        if vr == "UI":
            return generate_uid()
        if vr in {"IS", "DS"}:
            return "0"
        if vr in {"US", "UL", "SS", "SL", "SV", "UV"}:
            return 0
        if vr in {"FL", "FD"}:
            return 0.0
        if vr == "AS":
            return "000Y"
        if vr == "SQ":
            return Sequence([])
        if vr in {"OB", "OW", "OF", "OD", "OL", "OV", "UN"}:
            return b""
        return ""

    def suggest_required_ops(self, ds: Dataset, trigger_tag: int) -> AutoAddResult:
        trigger = f"{int(Tag(trigger_tag)):08X}"
        module_ids = set(self.tag_to_modules.get(trigger, []))
        if not module_ids:
            module_ids = set()

        sop_uid = str(getattr(ds, "SOPClassUID", ""))
        ciod = self.sop_to_ciod.get(sop_uid)
        if ciod:
            ciod_modules = set(self.ciod_to_modules.get(ciod, []))
            if ciod_modules:
                module_ids = module_ids.intersection(ciod_modules)

        required_tags: set[str] = set()
        for mid in module_ids:
            required_tags.update(self.module_required_tags.get(mid, []))

        # Add selected conditional-required tags for known trigger/value rules.
        trigger_elem = ds.get(Tag(int(trigger, 16)))
        if trigger_elem is not None:
            trigger_value = str(trigger_elem.value).strip().upper()
            conditional_map = CONDITIONAL_REQUIRED_BY_TRIGGER_VALUE.get(trigger, {})
            required_tags.update(conditional_map.get(trigger_value, []))

        ops: List[EditOperation] = []
        for tag_hex in sorted(required_tags):
            tag_int = int(tag_hex, 16)
            if tag_int in ds:
                continue
            if not self.registry.is_editable(tag_int):
                continue
            vr = self.registry.get_vr(tag_int)
            if not vr:
                continue
            value = self._default_value_for_vr(vr)
            ops.append(EditOperation(op="add", tag=tag_int, vr=vr, value=value, path=tag_hex))

        module_names = [self.module_names.get(mid, mid) for mid in sorted(module_ids)]
        return AutoAddResult(ops=ops, modules=module_names)
