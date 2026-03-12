from __future__ import annotations

from dataclasses import dataclass
from typing import List

from pydicom.dataset import Dataset
from pydicom.multival import MultiValue
from pydicom.sequence import Sequence


@dataclass(frozen=True)
class TagRow:
    path: str
    tag: str
    name: str
    vr: str
    value: str


def _render_value(value: object) -> str:
    if isinstance(value, Sequence):
        return f"<Sequence: {len(value)} items>"
    if isinstance(value, MultiValue):
        return "\\".join(str(v) for v in value)
    return str(value)


def _walk_dataset(ds: Dataset, base_path: str, out: List[TagRow]) -> None:
    for elem in ds:
        tag_hex = f"{elem.tag.group:04X}{elem.tag.element:04X}"
        this_path = f"{base_path}.{tag_hex}" if base_path else tag_hex
        out.append(
            TagRow(
                path=this_path,
                tag=f"({elem.tag.group:04X},{elem.tag.element:04X})",
                name=elem.name,
                vr=elem.VR,
                value=_render_value(elem.value),
            )
        )
        if isinstance(elem.value, Sequence):
            for idx, item in enumerate(elem.value):
                _walk_dataset(item, f"{this_path}[{idx}]", out)


def dataset_to_rows(ds: Dataset) -> List[TagRow]:
    rows: List[TagRow] = []
    _walk_dataset(ds, "", rows)
    rows.sort(key=lambda x: x.path)
    return rows


def parse_tag(text: str) -> int:
    t = text.strip().replace("(", "").replace(")", "").replace(",", "")
    if len(t) != 8:
        raise ValueError("Tag must be in format (GGGG,EEEE) or GGGGEEEE")
    return int(t, 16)
