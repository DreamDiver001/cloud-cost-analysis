import subprocess
import sys
from pathlib import Path

import pytest

from pipeline.run import build

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "focus_billing.csv"


@pytest.fixture(scope="session")
def con():
    if not DATA.exists():
        subprocess.run([sys.executable, str(ROOT / "generator" / "make_billing.py")], check=True)
    c = build(DATA)
    yield c
    c.close()
