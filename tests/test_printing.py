import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtCore import QMarginsF, QSize
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QApplication

from fotocarnet.layout import Corner, Settings, crop_rect, make_layout
from fotocarnet.printing import PrintError, new_printer, pages_to_print, print_document, printer_layout


class PrintingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "photos.pdf"
        self.image = QImage(400, 400, QImage.Format.Format_RGB32)
        self.image.fill(QColor("#ee1020"))
        self.crop = crop_rect(400, 400, 26, 32)
        self.printer = new_printer()
        self.printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        self.printer.setOutputFileName(str(self.path))
        self.printer.setResolution(300)
        self.printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

    def read_pdf(self):
        document = QPdfDocument()
        self.assertEqual(document.load(str(self.path)), QPdfDocument.Error.None_)
        self.assertEqual(document.status(), QPdfDocument.Status.Ready)
        return document

    def photo_bounds(self, document, page=0, size=QSize(840, 1188)):
        image = document.render(page, size).convertToFormat(QImage.Format.Format_RGBA8888)
        pixels = bytes(image.constBits())
        stride = image.bytesPerLine()
        positions = [
            ((offset % stride) // 4, offset // stride)
            for offset in range(0, len(pixels), 4)
            if pixels[offset] > 180 and pixels[offset + 1] < 70 and pixels[offset + 3] > 200
        ]
        self.assertTrue(positions, "El PDF debe contener la foto, no una hoja vacía.")
        return (
            min(x for x, _ in positions), min(y for _, y in positions),
            max(x for x, _ in positions) + 1, max(y for _, y in positions) + 1,
        )

    def test_pdf_uses_a4_and_exact_photo_dimensions_in_all_corners(self):
        for corner in Corner:
            with self.subTest(corner=corner):
                layout = printer_layout(self.printer, Settings(copies=1, corner=corner))
                print_document(self.printer, self.image, self.crop, layout)
                document = self.read_pdf()
                self.assertEqual(document.pageCount(), 1)
                page_size = document.pagePointSize(0)
                self.assertAlmostEqual(page_size.width() * 25.4 / 72, 210, delta=0.15)
                self.assertAlmostEqual(page_size.height() * 25.4 / 72, 297, delta=0.15)
                left, top, right, bottom = self.photo_bounds(document)
                expected = layout.positions(0)[0]
                self.assertAlmostEqual(left / 4, expected.x, delta=0.5)
                self.assertAlmostEqual(top / 4, expected.y, delta=0.5)
                self.assertAlmostEqual((right - left) / 4, 26, delta=0.5)
                self.assertAlmostEqual((bottom - top) / 4, 32, delta=0.5)
                document.close()

    def test_pdf_overflow_has_exact_page_count_and_corner_on_last_page(self):
        layout = printer_layout(self.printer, Settings(copies=113, corner=Corner.BOTTOM_RIGHT))
        print_document(self.printer, self.image, self.crop, layout)
        document = self.read_pdf()
        self.assertEqual(document.pageCount(), 3)
        left, top, right, bottom = self.photo_bounds(document, 2)
        self.assertAlmostEqual(left / 4, 179, delta=0.5)
        self.assertAlmostEqual(top / 4, 260, delta=0.5)
        self.assertAlmostEqual((right - left) / 4, 26, delta=0.5)
        self.assertAlmostEqual((bottom - top) / 4, 32, delta=0.5)
        document.close()

    def test_pdf_prints_the_selected_crop_not_the_whole_source(self):
        image = QImage(1000, 400, QImage.Format.Format_RGB32)
        image.fill(QColor("blue"))
        painter = QPainter(image)
        painter.fillRect(0, 0, 500, 400, QColor("#ee1020"))
        painter.end()
        crop = crop_rect(1000, 400, 26, 32, focus=(0, 0.5))
        layout = printer_layout(self.printer, Settings(copies=1))
        print_document(self.printer, image, crop, layout)
        document = self.read_pdf()
        rendered = document.render(0, QSize(840, 1188))
        for x, y in ((6, 6), (30, 6), (6, 36), (30, 36)):
            color = rendered.pixelColor(x * 4, y * 4)
            self.assertGreater(color.red(), 180)
            self.assertLess(color.blue(), 70)
        document.close()

    def test_landscape_keeps_physical_photo_size_and_corner(self):
        self.printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        layout = printer_layout(self.printer, Settings(copies=1, corner=Corner.BOTTOM_RIGHT))
        print_document(self.printer, self.image, self.crop, layout)
        document = self.read_pdf()
        self.assertGreater(document.pagePointSize(0).width(), document.pagePointSize(0).height())
        left, top, right, bottom = self.photo_bounds(document, size=QSize(1188, 840))
        self.assertAlmostEqual(left / 4, 266, delta=0.5)
        self.assertAlmostEqual(top / 4, 173, delta=0.5)
        self.assertAlmostEqual((right - left) / 4, 26, delta=0.5)
        self.assertAlmostEqual((bottom - top) / 4, 32, delta=0.5)
        document.close()

    def test_dialog_page_range_prints_only_selected_sheet(self):
        self.printer.setPrintRange(QPrinter.PrintRange.PageRange)
        self.printer.setFromTo(2, 2)
        layout = printer_layout(self.printer, Settings(copies=57))
        print_document(self.printer, self.image, self.crop, layout)
        document = self.read_pdf()
        self.assertEqual(document.pageCount(), 1)
        left, top, right, bottom = self.photo_bounds(document)
        self.assertAlmostEqual((right - left) / 4, 26, delta=0.5)
        self.assertAlmostEqual((bottom - top) / 4, 32, delta=0.5)
        document.close()

    def test_non_a4_and_invalid_ranges_do_not_start_printing(self):
        self.printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
        with self.assertRaisesRegex(ValueError, "A4"):
            printer_layout(self.printer, Settings())
        self.assertFalse(self.path.exists())
        self.printer.setPrintRange(QPrinter.PrintRange.PageRange)
        self.printer.setFromTo(2, 4)
        with self.assertRaisesRegex(ValueError, "intervalo"):
            print_document(self.printer, self.image, self.crop, make_layout(Settings()))
        self.assertFalse(self.path.exists())

    def test_cannot_write_pdf_is_an_explicit_failure(self):
        self.printer.setOutputFileName(str(self.path / "missing" / "photos.pdf"))
        with self.assertRaises(PrintError):
            print_document(self.printer, self.image, self.crop, make_layout(Settings()))

    def test_page_creation_failure_is_reported(self):
        with patch.object(self.printer, "newPage", return_value=False), self.assertRaisesRegex(PrintError, "siguiente hoja"):
            print_document(self.printer, self.image, self.crop, make_layout(Settings(copies=57)))

    def test_empty_image_is_not_printed(self):
        with self.assertRaisesRegex(ValueError, "foto"):
            print_document(self.printer, QImage(), self.crop, make_layout(Settings()))
        self.assertFalse(self.path.exists())

    def test_system_copies_collation_and_reverse_order(self):
        printer = Mock(spec=QPrinter)
        printer.printRange.return_value = QPrinter.PrintRange.AllPages
        printer.pageOrder.return_value = QPrinter.PageOrder.FirstPageFirst
        printer.copyCount.return_value = 2
        printer.supportsMultipleCopies.return_value = False
        printer.collateCopies.return_value = True
        layout = make_layout(Settings(copies=57))
        self.assertEqual(pages_to_print(printer, layout), (0, 1, 0, 1))
        printer.collateCopies.return_value = False
        self.assertEqual(pages_to_print(printer, layout), (0, 0, 1, 1))
        printer.pageOrder.return_value = QPrinter.PageOrder.LastPageFirst
        self.assertEqual(pages_to_print(printer, layout), (1, 1, 0, 0))
        printer.supportsMultipleCopies.return_value = True
        self.assertEqual(pages_to_print(printer, layout), (1, 0))


if __name__ == "__main__":
    unittest.main()
