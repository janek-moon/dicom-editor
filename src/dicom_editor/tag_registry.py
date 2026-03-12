from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import tempfile
import urllib.parse
import urllib.request
from typing import Dict, Optional

from pydicom.datadict import (
    DicomDictionary,
    dictionary_VR,
    dictionary_description,
    dictionary_is_retired,
)
from pydicom.tag import Tag


DEFAULT_ALLOWLIST_PATH = Path(__file__).with_name("data") / "innolitics_allowlist.json"
CACHE_ALLOWLIST_PATH = Path.home() / ".dicom-tag-editor" / "allowlist-cache.json"
DEFAULT_REMOTE_URL = os.environ.get("DICOM_ALLOWLIST_URL", "")


@dataclass(frozen=True)
class TagMeta:
    tag: int
    keyword: str
    vr: str
    retired: bool


class TagRegistry:
    """
    Standard-tag allowlist registry.

    Priority:
    1) Static embedded snapshot in repo
    2) Cached remote snapshot updated at runtime when internet is available
    3) pydicom built-in dictionary fallback
    """

    def __init__(
        self,
        allowlist_path: Optional[Path] = None,
        cache_path: Path = CACHE_ALLOWLIST_PATH,
        remote_url: str = DEFAULT_REMOTE_URL,
    ) -> None:
        self._meta_by_tag: Dict[int, TagMeta] = {}
        self._cache_path = cache_path

        path = allowlist_path or DEFAULT_ALLOWLIST_PATH
        loaded = False
        if path.exists():
            loaded = self._try_load_json(path)
        if not loaded and cache_path.exists():
            loaded = self._try_load_json(cache_path)
        if not loaded:
            self._load_from_pydicom_dictionary()

        if remote_url:
            self.try_update_from_remote(remote_url)

    def _try_load_json(self, path: Path) -> bool:
        try:
            self._load_from_json(path)
            return True
        except Exception:
            return False

    def _load_from_json(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        loaded: Dict[int, TagMeta] = {}
        for item in data:
            t = int(item["tag"], 16)
            loaded[t] = TagMeta(
                tag=t,
                keyword=item["name"],
                vr=item["vr"],
                retired=bool(item.get("retired", False)),
            )
        if not loaded:
            raise ValueError("allowlist is empty")
        self._meta_by_tag = loaded

    def _load_from_pydicom_dictionary(self) -> None:
        for raw_tag in DicomDictionary.keys():
            try:
                t = int(Tag(raw_tag))
                self._meta_by_tag[t] = TagMeta(
                    tag=t,
                    keyword=dictionary_description(t),
                    vr=dictionary_VR(t),
                    retired=bool(dictionary_is_retired(t)),
                )
            except Exception:
                continue

    def _fetch_remote_payload(self, remote_url: str, timeout_sec: float) -> str:
        parsed = urllib.parse.urlparse(remote_url)
        if parsed.scheme == "file":
            return Path(urllib.request.url2pathname(parsed.path)).read_text(encoding="utf-8")

        with urllib.request.urlopen(remote_url, timeout=timeout_sec) as resp:
            return resp.read().decode("utf-8")

    def try_update_from_remote(self, remote_url: str, timeout_sec: float = 2.0) -> bool:
        """Best-effort online update. Returns True only on successful refresh."""
        try:
            payload = self._fetch_remote_payload(remote_url, timeout_sec)
            data = json.loads(payload)
            if not isinstance(data, list) or not data:
                return False

            tmp_fd, tmp_path = tempfile.mkstemp(prefix="allowlist_", suffix=".json")
            try:
                Path(tmp_path).write_text(payload, encoding="utf-8")
                self._load_from_json(Path(tmp_path))
            finally:
                os.close(tmp_fd)
                Path(tmp_path).unlink(missing_ok=True)

            try:
                self._cache_path.parent.mkdir(parents=True, exist_ok=True)
                self._cache_path.write_text(payload, encoding="utf-8")
            except Exception:
                pass
            return True
        except Exception:
            return False

    def is_editable(self, tag: int) -> bool:
        return int(Tag(tag)) in self._meta_by_tag

    def get_meta(self, tag: int) -> Optional[TagMeta]:
        return self._meta_by_tag.get(int(Tag(tag)))

    def get_vr(self, tag: int) -> Optional[str]:
        meta = self.get_meta(tag)
        return meta.vr if meta else None

    def all_meta(self) -> list[TagMeta]:
        return list(self._meta_by_tag.values())


CRITICAL_DELETE_WARNING_TAGS = {
    int(Tag(0x00080018)),
    int(Tag(0x0020000D)),
    int(Tag(0x0020000E)),
    int(Tag(0x00100020)),
}
