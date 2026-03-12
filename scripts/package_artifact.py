from __future__ import annotations

import shutil
from pathlib import Path
import platform


def main() -> int:
    dist = Path('dist')
    name = 'DicomTagEditor'
    target_dir = dist / name
    target_exe = dist / f'{name}.exe'

    if target_dir.exists():
        src = target_dir
    elif target_exe.exists():
        src = target_exe
    else:
        raise SystemExit('Build output not found in dist/.')

    os_name = platform.system().lower()
    archive_base = dist / f'{name}-{os_name}'
    archive_path = shutil.make_archive(str(archive_base), 'zip', root_dir=src.parent, base_dir=src.name)
    print(archive_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
