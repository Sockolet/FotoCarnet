import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from fotocarnet.background import MODEL, composite_on_white, make_background_white
from fotocarnet.background_job import WhiteBackgroundJob


class CompositingTests(unittest.TestCase):
    def test_background_is_white_and_foreground_pixels_are_unchanged(self):
        image = Image.new("RGB", (3, 1), (20, 40, 80))
        original = image.tobytes()
        mask = Image.new("L", image.size)
        mask.putdata([0, 255, 128])
        result = composite_on_white(image, mask)
        self.assertEqual(result.size, image.size)
        self.assertEqual(result.mode, "RGB")
        self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(result.getpixel((1, 0)), (20, 40, 80))
        self.assertEqual(result.getpixel((2, 0)), (137, 147, 167))
        self.assertEqual(image.tobytes(), original)

    def test_original_transparency_is_composited_not_discarded(self):
        image = Image.new("RGBA", (2, 1), (255, 0, 0, 128))
        image.putpixel((1, 0), (0, 0, 255, 0))
        result = composite_on_white(image, Image.new("L", image.size, 255))
        self.assertEqual(result.getpixel((0, 0)), (255, 127, 127))
        self.assertEqual(result.getpixel((1, 0)), (255, 255, 255))

    def test_empty_detection_and_wrong_size_fail_explicitly(self):
        image = Image.new("RGB", (10, 20))
        with self.assertRaisesRegex(ValueError, "persona"):
            composite_on_white(image, Image.new("L", image.size, 0))
        with self.assertRaisesRegex(ValueError, "tamaño"):
            composite_on_white(image, Image.new("L", (20, 10), 255))

    def test_color_profile_is_preserved(self):
        image = Image.new("RGB", (10, 20))
        image.info["icc_profile"] = b"profile"
        result = composite_on_white(image, Image.new("L", image.size, 255))
        self.assertEqual(result.info["icc_profile"], b"profile")

    def test_model_is_explicitly_local_cpu_human_segmentation(self):
        image = Image.new("RGB", (10, 20), "red")
        rembg = Mock()
        rembg.remove.return_value = Image.new("L", image.size, 255)
        with patch.dict("sys.modules", {"rembg": rembg}), redirect_stderr(io.StringIO()):
            result = make_background_white(image)
        rembg.new_session.assert_called_once_with(MODEL, providers=["CPUExecutionProvider"])
        self.assertEqual(MODEL, "u2net_human_seg")
        rembg.remove.assert_called_once_with(image, session=rembg.new_session.return_value, only_mask=True)
        self.assertEqual(result.getpixel((0, 0)), (255, 0, 0))


class BackgroundJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def job(self, code: str) -> WhiteBackgroundJob:
        image = QImage(40, 60, QImage.Format.Format_RGB32)
        image.fill(QColor("#aa1122"))
        job = WhiteBackgroundJob(image)
        job.setArguments(["-c", code])
        return job

    def test_png_round_trip_through_local_process_and_progress(self):
        job = self.job(
            "import sys, time; "
            "sys.stderr.write('FOTOCARNET_'); sys.stderr.flush(); time.sleep(0.05); "
            "sys.stderr.write('PROCESSING\\n'); sys.stderr.flush(); "
            "sys.stdout.buffer.write(sys.stdin.buffer.read())"
        )
        result, error, progress = QSignalSpy(job.completed), QSignalSpy(job.failed), QSignalSpy(job.progress)
        finished = QSignalSpy(job.finished)
        self.assertEqual(job.processEnvironment().value("OMP_NUM_THREADS"), "2")
        job.start()
        self.assertTrue(finished.wait(5000))
        self.assertEqual(error.count(), 0)
        self.assertEqual(progress.count(), 1)
        self.assertEqual(result.count(), 1)
        image = result.at(0)[0]
        self.assertEqual((image.width(), image.height()), (40, 60))
        self.assertEqual(image.pixelColor(0, 0), QColor("#aa1122"))

    def test_failed_process_reports_diagnostics_not_an_image(self):
        job = self.job("import sys; sys.stdin.buffer.read(); sys.stderr.write('download failed'); sys.exit(7)")
        result, error, finished = QSignalSpy(job.completed), QSignalSpy(job.failed), QSignalSpy(job.finished)
        job.start()
        self.assertTrue(finished.wait(5000))
        self.assertEqual(result.count(), 0)
        self.assertEqual(error.count(), 1)
        self.assertIn("download failed", error.at(0)[0])

    def test_invalid_output_is_rejected_even_on_successful_exit(self):
        job = self.job("import sys; sys.stdin.buffer.read(); sys.stdout.write('not a PNG')")
        result, error, finished = QSignalSpy(job.completed), QSignalSpy(job.failed), QSignalSpy(job.finished)
        job.start()
        self.assertTrue(finished.wait(5000))
        self.assertEqual(result.count(), 0)
        self.assertEqual(error.count(), 1)
        self.assertIn("foto válida", error.at(0)[0])

    def test_cancellation_stops_process_without_reporting_a_failure(self):
        job = self.job("import sys, time; sys.stdin.buffer.read(); time.sleep(30)")
        result, error, finished = QSignalSpy(job.completed), QSignalSpy(job.failed), QSignalSpy(job.finished)
        job.start()
        QTimer.singleShot(80, job.cancel)
        self.assertTrue(finished.wait(5000))
        self.assertEqual(result.count(), 0)
        self.assertEqual(error.count(), 0)

    def test_missing_python_reports_start_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            job = self.job("")
            job.setProgram(str(Path(directory) / "missing-python"))
            error = QSignalSpy(job.failed)
            job.start()
            self.assertTrue(error.wait(5000))
            self.assertIn("iniciar", error.at(0)[0])


if __name__ == "__main__":
    unittest.main()
