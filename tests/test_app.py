"""Regression tests that run without opening a desktop window."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hydrant_app
from app_data import empty_hydrant, next_hydrant_reference
from file_utils import write_pdf_safely
from report_pdf import comments_layout


class RecordTests(unittest.TestCase):
    def test_new_records_do_not_share_photographs(self):
        first = empty_hydrant("HYD1")
        second = empty_hydrant("HYD2")
        first["photos"].append("first.jpg")
        self.assertEqual(second["photos"], [])
        self.assertEqual(second["hydrant_type"], "Underground")

    def test_reference_does_not_reuse_an_existing_number(self):
        records = [empty_hydrant("HYD1"), empty_hydrant("HYD3")]
        self.assertEqual(next_hydrant_reference(records), "HYD4")

    def test_comments_respect_line_breaks_and_pdf_width(self):
        self.assertTrue(comments_layout("Inspection completed.")[0])
        self.assertFalse(comments_layout("x\n" * 30)[0])
        text = ""
        while comments_layout(text + "Inspection completed. ")[0]:
            text += "Inspection completed. "
        self.assertTrue(comments_layout(text)[0])
        self.assertFalse(comments_layout(text + "Inspection completed. ")[0])


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.target = self.folder / "12345" / "12345_HYD1.pdf"
        self.app = hydrant_app.HydrantApp.__new__(hydrant_app.HydrantApp)
        self.app.inspections = [empty_hydrant("HYD1")]
        self.app.capture_current = Mock()
        self.app.shared_data = Mock(return_value={"job": "12345"})
        self.app.build_pdf = lambda shared, record, path: path.write_bytes(b"new PDF")
        self.dialogs = Mock()
        for name, value in [
            ("PDFS", self.folder),
            ("messagebox", self.dialogs),
            ("open_folder", Mock()),
        ]:
            patcher = patch.object(hydrant_app, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def existing_report(self):
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_bytes(b"existing PDF")

    def test_export_uses_job_and_hydrant_in_filename(self):
        self.dialogs.askyesno.return_value = True
        self.assertTrue(self.app.generate_all())
        self.assertEqual(self.target.read_bytes(), b"new PDF")

    def test_declining_replacement_keeps_original_and_returns_false(self):
        self.existing_report()
        self.dialogs.askyesno.side_effect = [True, False]
        self.assertFalse(self.app.generate_all())
        self.assertEqual(self.target.read_bytes(), b"existing PDF")

    def test_accepting_replacement_updates_original(self):
        self.existing_report()
        self.dialogs.askyesno.side_effect = [True, True]
        self.assertTrue(self.app.generate_all())
        self.assertEqual(self.target.read_bytes(), b"new PDF")

    def test_failed_export_preserves_original_and_removes_temporary_file(self):
        self.existing_report()
        self.dialogs.askyesno.return_value = True

        def fail(shared, record, path):
            path.write_bytes(b"partial PDF")
            raise RuntimeError("Failed to generate report")

        self.app.build_pdf = fail
        self.assertFalse(self.app.generate_all())
        self.assertEqual(self.target.read_bytes(), b"existing PDF")
        self.assertEqual(list(self.target.parent.iterdir()), [self.target])

    def test_invalid_date_stops_before_writing_files(self):
        self.app.shared_data.return_value["inspection_date"] = "31/02/2026"
        self.assertFalse(self.app.generate_all())
        self.assertFalse(self.target.exists())
        self.dialogs.showerror.assert_called_once()

    def test_folder_open_failure_does_not_invalidate_saved_reports(self):
        self.dialogs.askyesno.return_value = True
        with patch.object(hydrant_app, "open_folder", side_effect=OSError("Unavailable")):
            self.assertTrue(self.app.generate_all())
        self.assertEqual(self.target.read_bytes(), b"new PDF")
        self.dialogs.showwarning.assert_called_once()

    def test_atomic_writer_leaves_existing_report_on_failure(self):
        self.existing_report()

        def fail(shared, record, path):
            path.write_bytes(b"partial")
            raise ValueError("Invalid image")

        with self.assertRaises(ValueError):
            write_pdf_safely(fail, {}, {}, self.target)
        self.assertEqual(self.target.read_bytes(), b"existing PDF")


    def test_combined_export_uses_current_records_and_job_filename(self):
        self.dialogs.askyesno.return_value = True
        target = self.folder / "12345" / "12345_All_Hydrants.pdf"
        with patch.object(hydrant_app, "build_combined_pdf") as render:
            render.side_effect = lambda shared, records, path: path.write_bytes(b"combined")
            self.assertTrue(self.app.generate_combined())
            self.assertEqual(render.call_args.args[1], self.app.inspections)
        self.assertEqual(target.read_bytes(), b"combined")
        self.assertFalse(self.target.exists())

    def test_combined_replacement_declined(self):
        target = self.folder / "12345" / "12345_All_Hydrants.pdf"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing")
        self.dialogs.askyesno.side_effect = [True, False]
        with patch.object(hydrant_app, "build_combined_pdf") as render:
            self.assertFalse(self.app.generate_combined())
            render.assert_not_called()
        self.assertEqual(target.read_bytes(), b"existing")

    def test_combined_failure_preserves_existing_file(self):
        target = self.folder / "12345" / "12345_All_Hydrants.pdf"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"existing")
        self.dialogs.askyesno.return_value = True
        with patch.object(hydrant_app, "build_combined_pdf", side_effect=ValueError("Bad photo")):
            self.assertFalse(self.app.generate_combined())
        self.assertEqual(target.read_bytes(), b"existing")
        self.assertEqual(list(target.parent.iterdir()), [target])

    def test_combined_cancel_creates_no_files(self):
        self.dialogs.askyesno.return_value = False
        self.assertFalse(self.app.generate_combined())
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_combined_invalid_date_stops_export(self):
        self.app.shared_data.return_value["inspection_date"] = "31/02/2026"
        self.assertFalse(self.app.generate_combined())
        self.dialogs.askyesno.assert_not_called()

    def test_combined_empty_job_stops_export(self):
        self.app.inspections = []
        self.assertFalse(self.app.generate_combined())
        self.dialogs.showwarning.assert_called_once()


class NewJobTests(unittest.TestCase):
    def test_new_job_preserves_or_resets_form_according_to_export_result(self):
        for choice, exported, should_reset in [
            (None, True, False),
            (False, True, True),
            (True, True, True),
            (True, False, False),
        ]:
            with self.subTest(choice=choice, exported=exported):
                app = Mock()
                app.shared_vars = {"job": Mock(), "inspection_date": Mock()}
                app.inspections = ["current record"]
                app.generate_all.return_value = exported
                with patch.object(hydrant_app, "messagebox") as dialogs:
                    dialogs.askyesnocancel.return_value = choice
                    hydrant_app.HydrantApp.new_job(app)
                self.assertEqual(app.add_hydrant.called, should_reset)
                if not should_reset:
                    self.assertEqual(app.inspections, ["current record"])
                if choice is True:
                    app.generate_all.assert_called_once_with(confirm=False)
                else:
                    app.generate_all.assert_not_called()


class CombinedReportTests(unittest.TestCase):
    def test_combined_pdf_preserves_order_and_footer(self):
        from pypdf import PdfReader
        from report_pdf import build_combined_pdf

        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "combined.pdf"
            records = [empty_hydrant("HYD1"), empty_hydrant("HYD2")]
            build_combined_pdf({"job": "12345"}, records, output)
            pages = PdfReader(output).pages
            self.assertEqual(len(pages), 4)
            for index, page in enumerate(pages):
                ref = "HYD1" if index < 2 else "HYD2"
                text = page.extract_text()
                self.assertIn(f"12345 | {ref}", text)
                self.assertIn("© 2026 Erick L. Martins", text)
                self.assertIn("PHOTOGRAPHS" if index % 2 else "COMMENTS", text)

    def test_combined_pdf_rejects_empty_records(self):
        from report_pdf import build_combined_pdf

        with self.assertRaises(ValueError):
            build_combined_pdf({}, [], Path("unused.pdf"))


class WindowIconTests(unittest.TestCase):
    def test_windows_uses_approved_ico(self):
        root = Mock()
        with patch.object(hydrant_app.sys, "platform", "win32"):
            hydrant_app.set_window_icon(root)
        self.assertTrue(hydrant_app.APP_ICON_ICO.is_file())
        root.iconbitmap.assert_called_once_with(default=str(hydrant_app.APP_ICON_ICO))

    def test_macos_uses_approved_png_and_retains_image(self):
        root = Mock()
        with patch.object(hydrant_app.sys, "platform", "darwin"):
            with patch.object(hydrant_app.tk, "PhotoImage") as image:
                hydrant_app.set_window_icon(root)
        self.assertTrue(hydrant_app.APP_ICON_PNG.is_file())
        image.assert_called_once_with(master=root, file=str(hydrant_app.APP_ICON_PNG))
        root.iconphoto.assert_called_once_with(True, image.return_value)
        self.assertIs(root._app_icon, image.return_value)


if __name__ == "__main__":
    unittest.main()
