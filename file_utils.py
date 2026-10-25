"""Filesystem operations shared by the desktop app."""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PDFS = Path.home() / "Documents" / "HydrantReports" / "PDFs"


def safe_name(value):
    """Remove characters that Windows does not allow in filenames."""
    value = re.sub("[<>:\"/\\\\|?*\\x00-\\x1f]", "_", str(value).strip())
    return value[:100] or "Hydrant"


def open_folder(path):
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def write_pdf_safely(render, shared, record, output_file):
    """Leave the existing report untouched unless rendering finishes successfully."""
    output_file = Path(output_file)
    with tempfile.NamedTemporaryFile(
        dir=output_file.parent, suffix=".pdf", delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        render(shared, record, temporary_path)
        temporary_path.replace(output_file)
    finally:
        temporary_path.unlink(missing_ok=True)
