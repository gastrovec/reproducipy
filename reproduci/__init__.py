import sys
import os
from pathlib import Path

def get_root():
    """Change the CWD to the reproduci root."""
    cwd = Path(os.getcwd()).resolve()
    while not (cwd / "workdata").exists():
        cwd = cwd.parent
        if cwd.parent == cwd:
            raise RuntimeError("Can't find reproduci root")

    return cwd

ROOT = get_root()

def ensure_shebang(file):
    with open(file) as f:
        line = next(f)
    if sys.executable not in line:
        raise RuntimeError(f"""Shebang not found or faulty. Make sure it is exactly:
#!{sys.executable}""")
