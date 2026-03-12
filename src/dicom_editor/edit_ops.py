from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Optional

from pydicom.dataset import Dataset
from pydicom.sequence import Sequence
from pydicom.tag import Tag

from .tag_registry import TagRegistry

PATH_SEG_RE = re.compile(r"^([0-9A-Fa-f]{8})(?:\[(\d+)\])?$")


@dataclass(frozen=True)
class EditOperation:
    op: str  # update | add | remove
    tag: int
    value: Optional[str] = None
    vr: Optional[str] = None
    path: Optional[str] = None


class EditOpsEngine:
    def __init__(self, registry: TagRegistry) -> None:
        self.registry = registry

    def validate_editable(self, tag: int) -> None:
        if not self.registry.is_editable(tag):
            raise ValueError("Tag is outside the standard allowlist and cannot be edited.")

    def _normalize_path(self, path: Optional[str], fallback_tag: int) -> str:
        if path and path.strip():
            return path.strip().replace("(", "").replace(")", "").replace(",", "")
        return f"{fallback_tag:08X}"

    def _resolve_parent_and_tag(self, ds: Dataset, raw_path: str) -> tuple[Dataset, int]:
        segments = raw_path.split(".")
        if not segments:
            raise ValueError("Invalid path")

        current = ds
        for seg in segments[:-1]:
            m = PATH_SEG_RE.match(seg)
            if not m:
                raise ValueError(f"Invalid path segment: {seg}")
            tag = int(m.group(1), 16)
            idx = int(m.group(2) or 0)
            if tag not in current:
                raise ValueError(f"Sequence tag missing: {tag:08X}")
            elem = current[Tag(tag)]
            if not isinstance(elem.value, Sequence):
                raise ValueError(f"Path segment is not a sequence: {tag:08X}")
            if idx < 0 or idx >= len(elem.value):
                raise ValueError(f"Sequence index out of range for {tag:08X}[{idx}]")
            current = elem.value[idx]

        last = segments[-1]
        m = PATH_SEG_RE.match(last)
        if not m:
            raise ValueError(f"Invalid final path segment: {last}")
        target_tag = int(m.group(1), 16)
        if m.group(2) is not None:
            raise ValueError("Final path segment cannot include an index")
        return current, target_tag

    def apply_one(self, ds: Dataset, operation: EditOperation) -> None:
        raw_path = self._normalize_path(operation.path, operation.tag)
        parent_ds, tag = self._resolve_parent_and_tag(ds, raw_path)

        if operation.op in {"update", "add"}:
            self.validate_editable(tag)
            vr = operation.vr or self.registry.get_vr(tag)
            if not vr:
                raise ValueError("VR is required for this tag.")
            if operation.op == "update" and tag not in parent_ds:
                raise ValueError("Cannot update missing tag; use add instead.")
            parent_ds.add_new(Tag(tag), vr, operation.value)
            return

        if operation.op == "remove":
            if tag in parent_ds:
                del parent_ds[Tag(tag)]
            return

        raise ValueError(f"Unsupported operation: {operation.op}")

    def apply_all(self, ds: Dataset, operations: List[EditOperation]) -> Dataset:
        for op in operations:
            self.apply_one(ds, op)
        return ds
