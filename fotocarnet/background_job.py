import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QProcess, QProcessEnvironment, Signal
from PySide6.QtGui import QImage

from fotocarnet.background import PROCESSING_MARKER


class WhiteBackgroundJob(QProcess):
    completed = Signal(QImage)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self._size = image.size()
        self._cancelled = False
        self._diagnostics = ""
        self._processing = False
        self._input = QByteArray()
        buffer = QBuffer(self._input)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if image.isNull() or not image.save(buffer, "PNG"):
            raise ValueError("No se pudo preparar la foto para convertir el fondo.")
        buffer.close()
        self.setProgram(sys.executable)
        self.setArguments(["-m", "fotocarnet.background"])
        self.setWorkingDirectory(str(Path(__file__).resolve().parent.parent))
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("OMP_NUM_THREADS", "2")
        self.setProcessEnvironment(environment)
        self.started.connect(self._send_image)
        self.readyReadStandardError.connect(self._read_diagnostics)
        self.errorOccurred.connect(self._process_error)
        self.finished.connect(self._process_finished)
        self.finished.connect(self.deleteLater)

    def cancel(self):
        self._cancelled = True
        self.kill()

    def _send_image(self):
        self.write(self._input)
        self._input.clear()
        self.closeWriteChannel()

    def _read_diagnostics(self):
        self._diagnostics = (self._diagnostics + bytes(self.readAllStandardError()).decode("utf-8", errors="replace"))[-16000:]
        if PROCESSING_MARKER in self._diagnostics and not self._processing and not self._cancelled:
            self._processing = True
            self.progress.emit("Convirtiendo el fondo en blanco… La foto no sale de tu equipo.")

    def _process_error(self, error: QProcess.ProcessError):
        if error == QProcess.ProcessError.FailedToStart:
            if not self._cancelled:
                self.failed.emit(f"No se pudo iniciar el proceso local: {self.errorString()}")
            self.deleteLater()
        elif error in (QProcess.ProcessError.ReadError, QProcess.ProcessError.WriteError):
            self._diagnostics += f"\n{self.errorString()}"
            self.kill()

    def _process_finished(self, code: int, status: QProcess.ExitStatus):
        self._read_diagnostics()
        if self._cancelled:
            return
        if status != QProcess.ExitStatus.NormalExit or code != 0:
            self.failed.emit(f"El proceso de fondo blanco terminó con un error ({code}).\n\n{self._diagnostics}")
            return
        image = QImage.fromData(self.readAllStandardOutput(), "PNG")
        if image.isNull() or image.size() != self._size:
            self.failed.emit("El proceso no devolvió una foto válida del mismo tamaño. No se ha aplicado el cambio.")
            return
        self.completed.emit(image)
