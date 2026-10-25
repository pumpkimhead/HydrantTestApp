"""Field definitions and default inspection records."""

APP_TITLE = "Hydrant Test Report Manager"
APP_COPYRIGHT = "© 2026 Erick L. Martins. All rights reserved."
IMAGE_FILE_TYPES = [
    ("Image files", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
    ("All files", "*.*"),
]
STANDARD_PHOTO_LIMIT = 2

SHARED_FIELDS = [
    ("job", "Job Number", ""),
    ("location", "Site / Location", ""),
    ("inspection_date", "Inspection Date (DD/MM/YYYY)", ""),
    ("time", "Time (AM/PM)", ""),
    ("client", "Client", ""),
    ("next_date", "Next Inspection Due", ""),
    ("engineer", "Testing Engineer", ""),
    ("completed_by", "Report Completed By", ""),
]

HYDRANT_FIELDS = [
    ("ref", "Hydrant Reference", "HYD1"),
    ("hydrant_type", "Hydrant Type", "Underground"),
    ("depth", "Depth (mm)", ""),
    ("static", "Static Pressure", ""),
    ("residual", "Residual Pressure", ""),
    ("flow", "Flow Rate (L/min)", ""),
]

CHECKLIST = [
    ("cover", "Cover & frame sound"),
    ("working", "Is it in good working order?"),
    ("marker", "Marker plate present"),
]


def empty_hydrant(reference=""):
    """Create a blank inspection record."""
    record = {key: default for key, _, default in HYDRANT_FIELDS}

    record["ref"] = reference

    for key, _ in CHECKLIST:
        record[key] = "Yes"

    record["comments"] = ""
    record["photos"] = []
    record["horizontal_photo"] = ""

    return record


def next_hydrant_reference(records):
    references = {record.get("ref", "") for record in records}
    number = len(records) + 1
    while f"HYD{number}" in references:
        number += 1
    return f"HYD{number}"
