"""Desktop interface for preparing hydrant inspection reports."""

import sys
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app_data import (
    APP_TITLE, APP_COPYRIGHT, CHECKLIST, HYDRANT_FIELDS, SHARED_FIELDS,
    IMAGE_FILE_TYPES, STANDARD_PHOTO_LIMIT, empty_hydrant, next_hydrant_reference,
)
from file_utils import PDFS, open_folder, safe_name, write_pdf_safely
from report_pdf import build_pdf as render_report, build_combined_pdf, comments_layout


APP_ICON_PNG = Path(__file__).resolve().with_name("icon-hydrant-circular.png")
APP_ICON_ICO = Path(__file__).resolve().with_name("icon-hydrant-circular.ico")


def set_window_icon(root):
    if sys.platform == "win32":
        root.iconbitmap(default=str(APP_ICON_ICO))
    else:
        root._app_icon = tk.PhotoImage(master=root, file=str(APP_ICON_PNG))
        root.iconphoto(True, root._app_icon)


class HydrantApp:
    def __init__(self, root):
        self.root = root

        self.root.title(APP_TITLE)
        set_window_icon(self.root)
        self.root.geometry("1050x850")
        self.root.minsize(800, 650)

        self.shared_vars = {}
        self.hydrant_vars = {}
        self.inspections = []
        self.current_index = -1
        self.photo_paths = []
        self.horizontal_photo_path = ""

        self.build_ui()

        self.add_hydrant(first=True)

    def build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        ttk.Label(
            main, text="HYDRANT TEST REPORTS", font=("Segoe UI", 20, "bold")
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            main,
            text="Enter the job details once, then add each hydrant inspection.",
        ).grid(row=1, column=0, sticky="w", pady=(3, 12))
        self._build_job_details(main)

        lower = ttk.Panedwindow(main, orient="horizontal")
        lower.grid(row=3, column=0, sticky="nsew", pady=12)
        left = ttk.LabelFrame(lower, text="Hydrants in this job", padding=8)
        right = ttk.LabelFrame(lower, text="Selected Hydrant Inspection", padding=10)
        lower.add(left, weight=1)
        lower.add(right, weight=3)
        self._build_hydrant_list(left)
        self._build_hydrant_form(right)
        self._build_actions(main)

    def _build_job_details(self, main):
        shared = ttk.LabelFrame(main, text="JOB DETAILS", padding=10)

        shared.grid(row=2, column=0, sticky="ew")

        shared.columnconfigure(1, weight=1)
        shared.columnconfigure(3, weight=1)

        for i, (key, label, default) in enumerate(SHARED_FIELDS):
            row = i // 2
            col = (i % 2) * 2

            ttk.Label(shared, text=label).grid(
                row=row,
                column=col,
                sticky="w",
                padx=(0, 8),
                pady=4
            )

            if key == "inspection_date":
                default = date.today().strftime("%d/%m/%Y")
            variable = tk.StringVar(value=default)

            self.shared_vars[key] = variable

            ttk.Entry(shared, textvariable=variable).grid(
                row=row,
                column=col + 1,
                sticky="ew",
                padx=(0, 15),
                pady=4
            )

    def _build_hydrant_list(self, left):
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        self.inspection_list = tk.Listbox(left, width=23, exportselection=False)

        self.inspection_list.grid(row=0, column=0, sticky="nsew")

        self.inspection_list.bind("<<ListboxSelect>>", self.on_select)

        ttk.Button(left, text="+ Add Hydrant", command=self.add_hydrant).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(10, 4)
        )

        ttk.Button(left, text="Remove Selected", command=self.remove_hydrant).grid(
            row=2,
            column=0,
            sticky="ew",
            pady=4
        )

    def _build_hydrant_form(self, right):
        right.columnconfigure(1, weight=1)

        row = 0

        for key, label, default in HYDRANT_FIELDS:
            ttk.Label(right, text=label).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 10),
                pady=4
            )

            variable = tk.StringVar(value=default)

            self.hydrant_vars[key] = variable

            if key == "hydrant_type":
                widget = ttk.Combobox(
                    right,
                    textvariable=variable,
                    values=["Underground", "Pillar", "Other"]
                )
            else:
                widget = ttk.Entry(right, textvariable=variable)

            widget.grid(row=row, column=1, sticky="ew", pady=4)

            row += 1

        ttk.Separator(right).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

        row += 1

        ttk.Label(right, text="INSPECTION CHECKLIST", font=("Segoe UI", 11, "bold")).grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w"
        )

        row += 1

        for key, label in CHECKLIST:
            ttk.Label(right, text=label).grid(row=row, column=0, sticky="w", pady=4)

            variable = tk.StringVar(value="Yes")
            self.hydrant_vars[key] = variable

            ttk.Combobox(
                right,
                textvariable=variable,
                values=["Yes", "No", "N/A"],
                state="readonly",
                width=12
            ).grid(
                row=row,
                column=1,
                sticky="w",
                pady=4
            )

            row += 1

        ttk.Label(right, text="Comments").grid(row=row, column=0, sticky="nw", pady=5)

        self.comments_box = tk.Text(right, height=4, wrap="word")

        self.comments_box.grid(row=row, column=1, sticky="ew", pady=5)

        self._accepted_comments = ""
        self.comments_status = tk.StringVar(value="0 characters")
        ttk.Label(right, textvariable=self.comments_status).grid(
            row=row + 1, column=1, sticky="w"
        )
        self.comments_box.bind("<<Modified>>", self.validate_comments_edit)
        self.comments_box.edit_modified(False)

        row += 2

        row = self._build_photo_controls(right, row)

        ttk.Label(right, text=APP_COPYRIGHT).grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0)
        )

    def _build_photo_controls(self, right, row):
        ttk.Label(right, text="Photographs (maximum 3)").grid(
            row=row,
            column=0,
            sticky="nw",
            pady=5
        )

        photo_frame = ttk.Frame(right)

        photo_frame.grid(row=row, column=1, sticky="ew", pady=5)

        photo_frame.columnconfigure(0, weight=1)

        self.photo_label = tk.StringVar(value="No photographs selected")

        ttk.Label(photo_frame, textvariable=self.photo_label, wraplength=280).grid(
            row=0,
            column=0,
            sticky="w"
        )

        ttk.Button(photo_frame, text="Choose Photos", command=self.choose_photos).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4
        )

        ttk.Button(
            photo_frame,
            text="Choose Horizontal Photo",
            command=self.choose_horizontal_photo
        ).grid(
            row=1,
            column=1,
            columnspan=2,
            sticky="ew",
            padx=4,
            pady=4
        )
        self.horizontal_photo_label = tk.StringVar(value="No horizontal photo selected")

        ttk.Label(photo_frame, textvariable=self.horizontal_photo_label, wraplength=280).grid(
            row=1,
            column=0,
            sticky="w"
        )

        ttk.Button(photo_frame, text="Clear Photos", command=self.clear_photos).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=4
        )

        row += 1

        return row

    def _build_actions(self, main):
        actions = ttk.Frame(main)

        actions.grid(row=4, column=0, sticky="ew", pady=(0, 4))

        ttk.Button(actions, text="Generate All PDFs", command=self.generate_all).pack(
            side="left",
            padx=(0, 8)
        )

        ttk.Button(
            actions, text="Generate Single PDF", command=self.generate_combined
        ).pack(side="left", padx=(0, 8))

        ttk.Button(actions, text="New Job", command=self.new_job).pack(
            side="left",
            padx=(0, 8)
        )

        ttk.Button(actions, text="Open PDF Folder", command=self.open_pdf_folder).pack(
            side="right"
        )
    def validate_comments_edit(self, event=None):
        if not self.comments_box.edit_modified():
            return
        value = self.comments_box.get("1.0", "end-1c")
        fits, _ = comments_layout(value)
        if fits:
            self._accepted_comments = value
            self.comments_status.set(f"{len(value)} characters")
        else:
            cursor = self.comments_box.index("insert")
            self.comments_box.delete("1.0", "end")
            self.comments_box.insert("1.0", self._accepted_comments)
            self.comments_box.mark_set("insert", cursor)
            self.comments_status.set(
                f"{len(self._accepted_comments)} characters — PDF comment box limit reached"
            )
            self.root.bell()
        self.comments_box.edit_modified(False)

    def capture_current(self):
        if not 0 <= self.current_index < len(self.inspections):
            return

        record = self.inspections[self.current_index]

        for key, variable in self.hydrant_vars.items():
            record[key] = variable.get().strip()

        record["comments"] = self.comments_box.get("1.0", "end-1c").strip()

        record["photos"] = list(self.photo_paths)
        record["horizontal_photo"] = self.horizontal_photo_path

    def display_current(self):
        if not 0 <= self.current_index < len(self.inspections):
            return

        record = self.inspections[self.current_index]

        for key, variable in self.hydrant_vars.items():
            variable.set(record.get(key, ""))

        self.comments_box.delete("1.0", "end")

        self.comments_box.insert("1.0", record.get("comments", ""))

        self._accepted_comments = record.get("comments", "")
        self.comments_status.set(f"{len(self._accepted_comments)} characters")
        self.comments_box.edit_modified(False)

        self.photo_paths = list(record.get("photos", []))
        self.horizontal_photo_path = record.get("horizontal_photo", "")

        self.horizontal_photo_label.set(
            Path(self.horizontal_photo_path).name
            if self.horizontal_photo_path
            else "No horizontal photo selected"
        )

        self.update_photo_label()

        self.inspection_list.selection_clear(0, "end")

        self.inspection_list.selection_set(self.current_index)

        self.inspection_list.activate(self.current_index)

    def refresh_list(self):
        self.inspection_list.delete(0, "end")

        for index, record in enumerate(self.inspections, start=1):
            reference = record.get("ref", "").strip() or "New Hydrant"

            self.inspection_list.insert("end", f'{index}. {reference}')

    def on_select(self, event=None):
        selection = self.inspection_list.curselection()

        if not selection:
            return

        self.capture_current()

        self.current_index = selection[0]

        self.display_current()

    def add_hydrant(self, first=False):
        if not first:
            self.capture_current()

        reference = next_hydrant_reference(self.inspections)

        self.inspections.append(empty_hydrant(reference))

        self.current_index = len(self.inspections) - 1

        self.refresh_list()
        self.display_current()

    def remove_hydrant(self):
        selection = self.inspection_list.curselection()

        if not selection:
            messagebox.showwarning(
                "Select Hydrant",
                "Please select a hydrant to remove."
            )

            return

        if not messagebox.askyesno(
            "Remove Hydrant",
            "Remove this inspection from the current job?"
        ):
            return

        self.capture_current()

        del self.inspections[selection[0]]

        if not self.inspections:
            self.current_index = -1

            self.add_hydrant(first=True)

            return

        self.current_index = min(selection[0], len(self.inspections) - 1)

        self.refresh_list()
        self.display_current()

    def choose_photos(self):
        remaining = STANDARD_PHOTO_LIMIT - len(self.photo_paths)

        if remaining <= 0:
            messagebox.showinfo(
                "Photo Limit",
                "You have already selected two standard photos. "
                "Use the horizontal photo button for the third."
            )
            return

        filenames = filedialog.askopenfilenames(
            title="Choose Hydrant Photographs (maximum 2)",
            filetypes=IMAGE_FILE_TYPES
        )

        for filename in filenames:
            if len(self.photo_paths) >= STANDARD_PHOTO_LIMIT:
                break

            if filename not in self.photo_paths:
                self.photo_paths.append(filename)

        self.update_photo_label()
        self.capture_current()

    def choose_horizontal_photo(self):
        filename = filedialog.askopenfilename(
            title="Choose Horizontal Photograph",
            filetypes=IMAGE_FILE_TYPES
        )

        if not filename:
            return

        self.horizontal_photo_path = filename

        self.horizontal_photo_label.set(Path(filename).name)

        self.capture_current()

    def clear_photos(self):
        self.photo_paths = []
        self.horizontal_photo_path = ""

        self.photo_label.set("No photographs selected")
        self.horizontal_photo_label.set("No horizontal photo selected")

        self.capture_current()

    def update_photo_label(self):
        names = "\n".join(Path(path).name for path in self.photo_paths)
        self.photo_label.set(names or "No photographs selected")

    def shared_data(self):
        return {
            key: variable.get().strip()
            for key, variable in self.shared_vars.items()
        }

    def _validate_export(self, shared):
        for key in ("inspection_date", "next_date"):
            value = shared.get(key, "").strip()

            if value:
                try:
                    datetime.strptime(value, "%d/%m/%Y")
                except ValueError:
                    messagebox.showerror(
                        "Invalid Date",
                        f"{key.replace("_", " ").title()} "
                        "must use DD/MM/YYYY format (e.g. 21/10/2026)."
                    )
                    return False

        for record in self.inspections:
            if not comments_layout(record.get("comments", ""))[0]:
                messagebox.showerror(
                    "Comments Too Long",
                    f"Comments for {record.get("ref", "Hydrant")} exceed the PDF box. "
                    "Please shorten them before generating reports."
                )
                return False
        return True

    def _export_reports(self, shared, job_name, output_folder):
        """Write accepted reports and count any replacements the user declined."""
        created = 0
        skipped = 0
        for index, record in enumerate(self.inspections, start=1):
            reference = safe_name(record.get("ref") or f'HYD{index}')

            output_file = output_folder / f"{job_name}_{reference}.pdf"

            if output_file.exists() and not messagebox.askyesno(
                "Replace Existing PDF?",
                f"The file {output_file.name} already exists.\n\n"
                "Do you really want to replace it?\n"
                "Choose No to keep the existing report."
            ):
                skipped += 1
                continue

            write_pdf_safely(self.build_pdf, shared, record, output_file)
            created += 1

        return created, skipped

    def generate_all(self, confirm=True):
        self.capture_current()

        if not self.inspections:
            messagebox.showwarning("No Inspections", "Please add at least one hydrant.")
            return False

        shared = self.shared_data()

        if not self._validate_export(shared):
            return False

        if confirm and not messagebox.askyesno(
            "Generate PDF Reports",
            f"Generate {len(self.inspections)} separate PDF reports?"
        ):
            return False

        job_name = safe_name(shared.get("job") or shared.get("client") or "Job")

        output_folder = PDFS / job_name

        try:
            output_folder.mkdir(parents=True, exist_ok=True)
            created, skipped = self._export_reports(shared, job_name, output_folder)

            messagebox.showinfo(
                "PDFs Created",
                f"Created {created} individual reports.\n"
                f"Skipped {skipped} reports.\n\n"
                f"Saved in:\n{output_folder}"
            )
        except Exception as error:
            messagebox.showerror("PDF Generation Error", str(error))
            return False

        self._open_export_folder(output_folder)

        # A skipped PDF may contain older data, so New Job must keep the form.
        return skipped == 0

    def _open_export_folder(self, output_folder):
        try:
            open_folder(output_folder)
        except Exception as error:
            messagebox.showwarning(
                "Unable to Open Folder",
                f"The PDF export finished, but the folder could not be opened:\n{error}"
            )


    def generate_combined(self):
        self.capture_current()
        if not self.inspections:
            messagebox.showwarning("No Inspections", "Please add at least one hydrant.")
            return False

        shared = self.shared_data()
        if not self._validate_export(shared):
            return False
        if not messagebox.askyesno(
            "Generate Single PDF",
            f"Combine all {len(self.inspections)} hydrant reports into one PDF?"
        ):
            return False

        job_name = safe_name(shared.get("job") or shared.get("client") or "Job")
        output_folder = PDFS / job_name
        output_file = output_folder / f"{job_name}_All_Hydrants.pdf"
        try:
            output_folder.mkdir(parents=True, exist_ok=True)
            if output_file.exists() and not messagebox.askyesno(
                "Replace Existing PDF?",
                f"The file {output_file.name} already exists.\n\n"
                "Do you really want to replace it?"
            ):
                return False

            write_pdf_safely(build_combined_pdf, shared, self.inspections, output_file)
        except Exception as error:
            messagebox.showerror("PDF Generation Error", str(error))
            return False

        messagebox.showinfo(
            "PDF Created",
            f"Combined {len(self.inspections)} hydrant reports into one PDF.\n\n"
            f"Saved as:\n{output_file}"
        )
        self._open_export_folder(output_folder)
        return True

    def new_job(self):
        save_reports = messagebox.askyesnocancel(
            "Start a New Job",
            "You are creating a new form for a new job.\n"
            "The current job details and hydrant records will be cleared.\n\n"
            "Would you like to generate and save PDFs for the current job first?\n\n"
            "PDFs already saved will be kept. This does not save an editable job."
        )
        if save_reports is None:
            return
        if save_reports and not self.generate_all(confirm=False):
            messagebox.showinfo(
                "Current Job Kept",
                "A new job was not started because not all current reports were saved. "
                "The current form has been kept."
            )
            return

        for key, variable in self.shared_vars.items():
            if key == "inspection_date":
                variable.set(date.today().strftime("%d/%m/%Y"))
            else:
                variable.set("")

        self.inspections = []
        self.current_index = -1
        self.photo_paths = []
        self.horizontal_photo_path = ""
        self.horizontal_photo_label.set("No horizontal photo selected")

        self.add_hydrant(first=True)

    def open_pdf_folder(self):
        open_folder(PDFS)

    @staticmethod
    def build_pdf(shared, record, output_file):
        render_report(shared, record, output_file)


def main():
    root = tk.Tk()
    HydrantApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
