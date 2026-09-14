import tempfile
import unittest
import struct
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QMarginsF, QObject, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPageLayout, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from fotocarnet.app import MainWindow


class ControlledBackgroundJob(QObject):
    completed = Signal(QImage)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.image = QImage(image)
        self.cancelled = False

    def start(self):
        pass

    def cancel(self):
        self.cancelled = True

    def waitForFinished(self, timeout):
        return True


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.addCleanup(self.window.close)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "photo.png"
        image = QImage(600, 800, QImage.Format.Format_RGB32)
        image.fill(QColor("#bb5544"))
        self.assertTrue(image.save(str(self.path)))

    def load(self):
        self.assertTrue(self.window.load_photo(str(self.path)))

    def pdf_destination(self):
        destination = Path(self.temporary.name) / "output.pdf"
        self.window.printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        self.window.printer.setOutputFileName(str(destination))
        self.window.printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
        return destination

    def test_photo_is_required_and_loading_enables_printing(self):
        self.assertFalse(self.window.print_button.isEnabled())
        self.load()
        self.assertTrue(self.window.print_button.isEnabled())
        self.assertEqual(self.window.filename.text(), "photo.png")
        crop = self.window.crop_view.source_rect()
        self.assertAlmostEqual(crop.width / crop.height, 26 / 32)

    def test_corrupt_photo_reports_error_and_preserves_previous_image(self):
        self.load()
        image_key = self.window.crop_view.image.cacheKey()
        with patch("fotocarnet.app.QMessageBox.warning") as warning:
            self.assertFalse(self.window.load_photo(str(self.path / "missing.png")))
            warning.assert_called_once()
        self.assertEqual(self.window.crop_view.image.cacheKey(), image_key)

    def test_phone_exif_orientation_is_applied(self):
        image = QImage(40, 80, QImage.Format.Format_RGB32)
        image.fill(QColor("#bb5544"))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        self.assertTrue(image.save(buffer, "JPEG"))
        buffer.close()
        exif = (
            b"Exif\x00\x00II" + struct.pack("<HIH", 42, 8, 1)
            + struct.pack("<HHI", 0x0112, 3, 1)
            + struct.pack("<H", 6) + b"\x00\x00" + struct.pack("<I", 0)
        )
        jpeg = bytes(data)
        path = Path(self.temporary.name) / "phone.jpg"
        path.write_bytes(jpeg[:2] + b"\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif + jpeg[2:])
        self.assertTrue(self.window.load_photo(str(path)))
        self.assertEqual((self.window.crop_view.image.width(), self.window.crop_view.image.height()), (80, 40))

    def test_presets_custom_dimensions_zoom_and_new_photo(self):
        self.load()
        self.window.preset.setCurrentIndex(1)
        self.assertEqual((self.window.settings().width, self.window.settings().height), (35, 45))
        self.window.photo_width.setValue(30)
        self.assertEqual(self.window.preset.currentText(), "Personalizado")
        before = self.window.crop_view.source_rect()
        self.window.zoom.setValue(200)
        after = self.window.crop_view.source_rect()
        self.assertAlmostEqual(after.width, before.width / 2)
        self.assertAlmostEqual(after.height, before.height / 2)
        self.load()
        self.assertEqual(self.window.zoom.value(), 100)
        self.assertEqual(self.window.crop_view.zoom, 1)

    def test_dragging_changes_crop_in_preview_without_changing_original(self):
        self.load()
        self.window.show()
        self.app.processEvents()
        self.window.zoom.setValue(200)
        crop_view = self.window.crop_view
        center = crop_view.display_rect().center().toPoint()
        image_key = crop_view.image.cacheKey()
        before = crop_view.source_rect()
        QTest.mousePress(crop_view, Qt.MouseButton.LeftButton, pos=center)
        QTest.mouseMove(crop_view, center - QPoint(25, 20))
        QTest.mouseRelease(crop_view, Qt.MouseButton.LeftButton, pos=center - QPoint(25, 20))
        after = crop_view.source_rect()
        self.assertGreater(after.x, before.x)
        self.assertGreater(after.y, before.y)
        self.assertEqual(after, self.window.preview.crop)
        self.assertEqual(image_key, crop_view.image.cacheKey())

    def test_page_selection_clamps_when_copy_count_shrinks(self):
        self.window.copies.setValue(57)
        self.window.page_selector.setValue(2)
        self.assertEqual(self.window.preview.page, 1)
        self.window.copies.setValue(1)
        self.assertEqual(self.window.preview.page, 0)
        self.assertEqual(self.window.page_selector.maximum(), 1)

    def test_impossible_photo_size_disables_printing_and_recovers(self):
        self.load()
        self.window.photo_width.setValue(297)
        self.assertFalse(self.window.print_button.isEnabled())
        self.assertIn("no cabe", self.window.summary.text())
        self.window.photo_width.setValue(26)
        self.assertTrue(self.window.print_button.isEnabled())

    def test_cancelling_system_dialog_does_not_print(self):
        self.load()
        with patch("fotocarnet.app.QPrintDialog") as dialog, patch("fotocarnet.app.print_document") as printing:
            dialog.return_value.exec.return_value = QDialog.DialogCode.Rejected
            self.window.print_button.click()
            dialog.assert_called_once_with(self.window.printer, self.window)
            printing.assert_not_called()

    def test_accepting_dialog_creates_pdf_with_chosen_number_of_sheets(self):
        self.load()
        destination = self.pdf_destination()
        self.window.copies.setValue(57)
        with patch("fotocarnet.app.QPrintDialog") as dialog, patch("fotocarnet.app.QMessageBox.warning") as warning:
            dialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
            self.window.print_button.click()
            warning.assert_not_called()
        document = QPdfDocument()
        self.assertEqual(document.load(str(destination)), QPdfDocument.Error.None_)
        self.assertEqual(document.pageCount(), 2)
        document.close()

    def test_orientation_updates_preview_but_declining_does_not_print(self):
        self.load()
        destination = self.pdf_destination()
        self.window.margin.setValue(10)
        self.window.printer.setPageMargins(QMarginsF(3, 3, 3, 3), QPageLayout.Unit.Millimeter)
        self.window.printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        with patch("fotocarnet.app.QPrintDialog") as dialog, patch("fotocarnet.app.QMessageBox.question") as question:
            dialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
            question.return_value = QMessageBox.StandardButton.No
            self.window.print_button.click()
            question.assert_called_once()
        self.assertFalse(destination.exists())
        self.assertEqual(self.window.paper_size, (297, 210))
        self.window.margin.setValue(0)
        self.assertAlmostEqual(self.window.current_layout.margins.left, 3, delta=0.1)

    def test_white_background_is_optional_reversible_and_cached(self):
        self.assertFalse(self.window.white_background.isEnabled())
        self.load()
        self.assertFalse(self.window.white_background.isChecked())
        original = self.window.crop_view.image.cacheKey()
        self.window.zoom.setValue(150)
        self.window.crop_view.focus = (0.3, 0.7)
        layout = self.window.current_layout
        crop = self.window.crop_view.source_rect()
        processed = QImage(self.window.crop_view.image.size(), QImage.Format.Format_RGB32)
        processed.fill(QColor("white"))
        with patch("fotocarnet.app.WhiteBackgroundJob", ControlledBackgroundJob):
            self.window.white_background.setChecked(True)
            job = self.window._background_job
            self.assertEqual(job.image.cacheKey(), original)
            self.assertFalse(self.window.print_button.isEnabled())
            job.completed.emit(processed)
            self.assertTrue(self.window.print_button.isEnabled())
            self.assertEqual(self.window.preview.image.cacheKey(), processed.cacheKey())
            self.assertEqual(self.window.crop_view.source_rect(), crop)
            self.assertEqual(self.window.current_layout, layout)
            self.window.white_background.setChecked(False)
            self.assertEqual(self.window.preview.image.cacheKey(), original)
            self.window.white_background.setChecked(True)
            self.assertIsNone(self.window._background_job)
            self.assertEqual(self.window.preview.image.cacheKey(), processed.cacheKey())

    def test_printing_waits_for_background_and_uses_processed_photo(self):
        self.load()
        destination = self.pdf_destination()
        processed = QImage(self.window.crop_view.image.size(), QImage.Format.Format_RGB32)
        processed.fill(QColor("white"))
        painter = QPainter(processed)
        painter.fillRect(120, 120, 360, 560, QColor("#bb5544"))
        painter.end()
        with patch("fotocarnet.app.WhiteBackgroundJob", ControlledBackgroundJob):
            self.window.white_background.setChecked(True)
            self.window.copies.setValue(8)
            self.assertFalse(self.window.print_button.isEnabled())
            with patch("fotocarnet.app.QMessageBox.information") as notice, patch("fotocarnet.app.QPrintDialog") as dialog:
                self.window.print_photos()
                notice.assert_called_once()
                dialog.assert_not_called()
            self.window._background_job.completed.emit(processed)
            with patch("fotocarnet.app.QPrintDialog") as dialog:
                dialog.return_value.exec.return_value = QDialog.DialogCode.Accepted
                self.window.print_button.click()
        document = QPdfDocument()
        self.assertEqual(document.load(str(destination)), QPdfDocument.Error.None_)
        self.assertEqual(document.pageCount(), 1)
        page = document.render(0, QSize(840, 1188))
        self.assertEqual(page.pixelColor(24, 24), QColor("white"))
        # El backend PDF puede recomprimir la imagen con JPEG.
        printed = page.pixelColor(72, 84).getRgb()
        self.assertLessEqual(max(abs(a - b) for a, b in zip(printed[:3], (187, 85, 68))), 2)
        self.assertEqual(printed[3], 255)
        document.close()

    def test_unchecking_cancels_and_ignores_a_late_result(self):
        self.load()
        original = self.window.crop_view.image.cacheKey()
        with patch("fotocarnet.app.WhiteBackgroundJob", ControlledBackgroundJob):
            self.window.white_background.setChecked(True)
            job = self.window._background_job
            self.window.white_background.setChecked(False)
            self.assertTrue(job.cancelled)
            self.assertTrue(self.window.print_button.isEnabled())
            job.completed.emit(QImage(600, 800, QImage.Format.Format_RGB32))
            self.assertEqual(self.window.crop_view.image.cacheKey(), original)
            self.assertTrue(self.window._white_image.isNull())

    def test_opening_another_photo_cancels_and_ignores_previous_result(self):
        self.load()
        with patch("fotocarnet.app.WhiteBackgroundJob", ControlledBackgroundJob):
            self.window.white_background.setChecked(True)
            job = self.window._background_job
            self.load()
            new_image = self.window.crop_view.image.cacheKey()
            self.assertTrue(job.cancelled)
            self.assertFalse(self.window.white_background.isChecked())
            job.completed.emit(QImage(600, 800, QImage.Format.Format_RGB32))
            self.assertEqual(self.window.crop_view.image.cacheKey(), new_image)

    def test_failed_conversion_restores_original_and_can_retry(self):
        self.load()
        original = self.window.crop_view.image.cacheKey()
        with patch("fotocarnet.app.WhiteBackgroundJob", ControlledBackgroundJob), patch("fotocarnet.app.QMessageBox.exec") as warning:
            self.window.white_background.setChecked(True)
            self.window._background_job.failed.emit("No connection")
            warning.assert_called_once()
            self.assertFalse(self.window.white_background.isChecked())
            self.assertIsNone(self.window._background_job)
            self.assertEqual(self.window.preview.image.cacheKey(), original)
            self.assertTrue(self.window.print_button.isEnabled())
            self.window.white_background.setChecked(True)
            self.assertIsNotNone(self.window._background_job)
            self.window.white_background.setChecked(False)

    def test_closing_cancels_pending_background_processing(self):
        self.load()
        with patch("fotocarnet.app.WhiteBackgroundJob", ControlledBackgroundJob):
            self.window.white_background.setChecked(True)
            job = self.window._background_job
            self.window.close()
            self.assertTrue(job.cancelled)
            self.assertIsNone(self.window._background_job)


if __name__ == "__main__":
    unittest.main()
