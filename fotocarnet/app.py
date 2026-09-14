from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor, QImage, QImageReader, QKeySequence, QPainter, QPalette, QPen, QShortcut
from PySide6.QtPrintSupport import QPrintDialog
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from fotocarnet.background_job import WhiteBackgroundJob
from fotocarnet.layout import Corner, Layout, Margins, Rect, Settings, crop_rect, make_layout
from fotocarnet.printing import (
    PrintError, draw_photos, new_printer, print_document, printer_layout, printer_margins,
)


class PhotoCrop(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.image = QImage()
        self.photo_size = (26.0, 32.0)
        self.focus = (0.5, 0.5)
        self.zoom = 1.0
        self._last_position: QPointF | None = None
        self.setFixedHeight(174)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAccessibleName("Encuadre de la foto; arrastra para moverla")

    def source_rect(self) -> Rect | None:
        if self.image.isNull():
            return None
        return crop_rect(self.image.width(), self.image.height(), *self.photo_size, self.focus, self.zoom)

    def display_rect(self) -> QRectF:
        width, height = self.photo_size
        scale = min((self.width() - 12) / width, (self.height() - 8) / height)
        return QRectF((self.width() - width * scale) / 2, 4, width * scale, height * scale)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.display_rect()
        painter.fillRect(rect, QColor("#ffffff"))
        source = self.source_rect()
        if source is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(rect, self.image, QRectF(source.x, source.y, source.width, source.height))
        else:
            painter.setPen(QColor("#74817c"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Tu foto")
        painter.setPen(QPen(QColor("#91a69d"), 1))
        painter.drawRect(rect)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.image.isNull() and self.display_rect().contains(event.position()):
            self._last_position = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        source = self.source_rect()
        if self._last_position is not None and source is not None:
            delta = event.position() - self._last_position
            self._last_position = event.position()
            scale = self.display_rect().width() / source.width
            free_x = self.image.width() - source.width
            free_y = self.image.height() - source.height
            x = self.focus[0] - delta.x() / scale / free_x if free_x > 1e-8 else self.focus[0]
            y = self.focus[1] - delta.y() / scale / free_y if free_y > 1e-8 else self.focus[1]
            self.focus = (max(0, min(1, x)), max(0, min(1, y)))
            self.update()
            self.changed.emit()

    def mouseReleaseEvent(self, event):
        self._last_position = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)


class PaperPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.layout_data: Layout | None = None
        self.image = QImage()
        self.crop: Rect | None = None
        self.page = 0
        self.setMinimumSize(320, 380)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Vista previa del folio DIN A4")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e5ebe7"))
        layout = self.layout_data
        if layout is not None:
            scale = min((self.width() - 48) / layout.paper_width, (self.height() - 48) / layout.paper_height)
            paper = QRectF(
                (self.width() - layout.paper_width * scale) / 2,
                (self.height() - layout.paper_height * scale) / 2,
                layout.paper_width * scale, layout.paper_height * scale,
            )
            painter.fillRect(paper.translated(3, 4), QColor("#cbd5ce"))
            painter.fillRect(paper, Qt.GlobalColor.white)
            painter.translate(paper.topLeft())
            painter.scale(scale, scale)
            positions = layout.positions(self.page)
            if self.crop is not None and not self.image.isNull():
                draw_photos(painter, self.image, self.crop, positions)
            else:
                for rect in positions:
                    painter.fillRect(QRectF(rect.x, rect.y, rect.width, rect.height), QColor("#d6e7df"))
            painter.setPen(QPen(QColor("#9daea5"), 0.15))
            for rect in positions:
                painter.drawRect(QRectF(rect.x, rect.y, rect.width, rect.height))
        painter.end()


def millimeter_input(value: float, maximum: float) -> QDoubleSpinBox:
    control = QDoubleSpinBox()
    control.setRange(0, maximum)
    control.setDecimals(1)
    control.setSuffix(" mm")
    control.setValue(value)
    control.setKeyboardTracking(False)
    return control


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FotoCarnet")
        self.resize(1040, 790)
        self.printer = new_printer()
        self.paper_size = (210.0, 297.0)
        self.minimum_margins = Margins()
        self.current_layout: Layout | None = None
        self._original_image = QImage()
        self._white_image = QImage()
        self._background_job: WhiteBackgroundJob | None = None

        root = QWidget()
        root.setObjectName("content")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 18, 24, 18)
        title = QLabel("FotoCarnet")
        title.setObjectName("title")
        outer.addWidget(title)
        subtitle = QLabel("Tus fotos en una esquina. El resto del folio, libre.")
        subtitle.setObjectName("muted")
        outer.addWidget(subtitle)
        body = QHBoxLayout()
        body.setSpacing(24)
        outer.addLayout(body, 1)

        sidebar = QWidget()
        sidebar.setFixedWidth(310)
        controls = QVBoxLayout(sidebar)
        controls.setContentsMargins(0, 8, 12, 0)
        controls.setSpacing(9)
        choose = QPushButton("Elegir foto…")
        choose.clicked.connect(self.open_photo)
        controls.addWidget(choose)
        self.filename = QLabel("JPG, PNG, WebP, TIFF o BMP · todo local")
        self.filename.setTextFormat(Qt.TextFormat.PlainText)
        self.filename.setWordWrap(True)
        self.filename.setObjectName("muted")
        controls.addWidget(self.filename)
        self.crop_view = PhotoCrop()
        self.crop_view.changed.connect(self.refresh)
        controls.addWidget(self.crop_view)

        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("Zoom"))
        self.zoom = QSlider(Qt.Orientation.Horizontal)
        self.zoom.setRange(100, 300)
        self.zoom.setValue(100)
        self.zoom.setEnabled(False)
        self.zoom.setAccessibleName("Zoom del encuadre")
        self.zoom.valueChanged.connect(self.change_zoom)
        zoom_row.addWidget(self.zoom)
        controls.addLayout(zoom_row)
        crop_hint = QLabel("Arrastra para encuadrar. No se estira.")
        crop_hint.setObjectName("muted")
        controls.addWidget(crop_hint)
        self.white_background = QCheckBox("Fondo blanco automático")
        palette = self.white_background.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        self.white_background.setPalette(palette)
        self.white_background.setEnabled(False)
        self.white_background.setToolTip(
            "Separa a la persona y pone el fondo blanco, sin subir la foto.\n"
            "La primera vez descarga un modelo de unos 176 MB.\n"
            "Desmarca la opción para volver al original o cancelar."
        )
        self.white_background.toggled.connect(self.toggle_white_background)
        controls.addWidget(self.white_background)

        form = QFormLayout()
        form.setVerticalSpacing(10)
        self.copies = QSpinBox()
        self.copies.setRange(1, 9999)
        self.copies.setValue(6)
        self.copies.setKeyboardTracking(False)
        self.copies.valueChanged.connect(self.refresh)
        form.addRow("Fotos en total", self.copies)
        self.preset = QComboBox()
        self.preset.addItem("Carnet · 26 × 32 mm", (26, 32))
        self.preset.addItem("35 × 45 mm", (35, 45))
        self.preset.addItem("2 × 2 pulgadas", (50.8, 50.8))
        self.preset.addItem("Personalizado", None)
        self.preset.currentIndexChanged.connect(self.apply_preset)
        form.addRow("Tamaño", self.preset)
        self.photo_width = millimeter_input(26, 297)
        self.photo_height = millimeter_input(32, 297)
        self.photo_width.setMinimum(1)
        self.photo_height.setMinimum(1)
        self.photo_width.valueChanged.connect(self.dimensions_changed)
        self.photo_height.valueChanged.connect(self.dimensions_changed)
        dimensions = QHBoxLayout()
        dimensions.setSpacing(4)
        dimensions.addWidget(self.photo_width)
        dimensions.addWidget(QLabel("×"))
        dimensions.addWidget(self.photo_height)
        self.photo_width.setAccessibleName("Ancho de la foto en milímetros")
        self.photo_height.setAccessibleName("Alto de la foto en milímetros")
        form.addRow("Ancho × alto", dimensions)
        self.corner = QComboBox()
        for corner in Corner:
            self.corner.addItem(corner.value, corner)
        self.corner.currentIndexChanged.connect(self.refresh)
        form.addRow("Esquina", self.corner)
        self.margin = millimeter_input(5, 100)
        self.margin.valueChanged.connect(self.refresh)
        form.addRow("Margen mínimo", self.margin)
        self.gap = millimeter_input(2, 30)
        self.gap.valueChanged.connect(self.refresh)
        form.addRow("Entre fotos", self.gap)
        controls.addLayout(form)
        controls.addStretch()
        self.print_button = QPushButton("Imprimir…")
        self.print_button.setObjectName("primary")
        self.print_button.setMinimumHeight(44)
        self.print_button.clicked.connect(self.print_photos)
        controls.addWidget(self.print_button)
        print_hint = QLabel("Abre el diálogo de impresión.\nPapel A4 · escala 100 % · 1 página por cara.")
        print_hint.setWordWrap(True)
        print_hint.setObjectName("muted")
        controls.addWidget(print_hint)
        scroll = QScrollArea()
        scroll.setWidget(sidebar)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setFixedWidth(330)
        body.addWidget(scroll)

        right = QVBoxLayout()
        preview_heading = QHBoxLayout()
        self.paper_label = QLabel("DIN A4 · 210 × 297 mm")
        preview_heading.addWidget(self.paper_label)
        preview_heading.addStretch()
        preview_heading.addWidget(QLabel("Hoja"))
        self.page_selector = QSpinBox()
        self.page_selector.setRange(1, 1)
        self.page_selector.valueChanged.connect(self.change_page)
        preview_heading.addWidget(self.page_selector)
        right.addLayout(preview_heading)
        self.preview = PaperPreview()
        right.addWidget(self.preview, 1)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        right.addWidget(self.summary)
        note = QLabel("Solo se imprimen las fotos, no los bordes de la vista previa.\nLa impresora puede necesitar un margen mayor para no recortarlas.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        right.addWidget(note)
        body.addLayout(right, 1)
        root.setStyleSheet("""
            QWidget#content, QScrollArea, QScrollArea > QWidget > QWidget { background: #f6f8f5; }
            QWidget { color: #22382d; font-size: 13px; }
            QLabel#title { font-size: 29px; font-weight: 700; }
            QLabel#muted { color: #63766b; font-size: 12px; }
            QPushButton { background: #e3ebe6; border: 1px solid #bccbc2; border-radius: 6px; padding: 8px; }
            QPushButton:hover { background: #d5e3da; }
            QPushButton#primary { background: #216d4d; color: white; border: none; font-weight: 600; }
            QPushButton#primary:hover { background: #18543b; }
            QPushButton:disabled { background: #dce4df; color: #89988f; }
            QSpinBox, QDoubleSpinBox, QComboBox { background: white; color: #22382d; min-height: 25px; }
        """)
        QShortcut(QKeySequence.StandardKey.Open, self, activated=self.open_photo)
        QShortcut(QKeySequence.StandardKey.Print, self, activated=self.print_photos)
        self.refresh()

    def settings(self) -> Settings:
        return Settings(
            self.photo_width.value(), self.photo_height.value(), self.copies.value(),
            self.corner.currentData(), self.margin.value(), self.gap.value(),
        )

    def open_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Elegir foto", "",
            "Imágenes (*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp);;Todos los archivos (*)",
        )
        if path:
            self.load_photo(path)

    def load_photo(self, path: str) -> bool:
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        reader.setDecideFormatFromContent(True)
        image = reader.read()
        if image.isNull():
            QMessageBox.warning(self, "No se pudo abrir la foto", reader.errorString())
            return False
        self.cancel_background()
        self._original_image = image
        self._white_image = QImage()
        with QSignalBlocker(self.white_background):
            self.white_background.setChecked(False)
        self.white_background.setEnabled(True)
        self.crop_view.image = image
        self.crop_view.focus = (0.5, 0.5)
        self.zoom.setValue(100)
        self.zoom.setEnabled(True)
        self.filename.setText(Path(path).name)
        self.filename.setToolTip(str(Path(path)))
        self.refresh()
        return True

    def cancel_background(self):
        if self._background_job is not None:
            job = self._background_job
            self._background_job = None
            job.cancel()
            self.statusBar().showMessage("Conversión cancelada. Se conserva la foto original.", 6000)

    def toggle_white_background(self, enabled: bool):
        if not enabled:
            self.cancel_background()
            self.crop_view.image = self._original_image
            self.statusBar().showMessage("Foto original restaurada.", 6000)
        elif not self._white_image.isNull():
            self.crop_view.image = self._white_image
            self.statusBar().showMessage("Fondo blanco aplicado. Revisa el pelo y los bordes antes de imprimir.", 12000)
        else:
            try:
                job = WhiteBackgroundJob(self._original_image, self)
            except ValueError as error:
                with QSignalBlocker(self.white_background):
                    self.white_background.setChecked(False)
                QMessageBox.warning(self, "No se pudo preparar la foto", str(error))
                return
            self._background_job = job
            job.completed.connect(lambda image: self.background_completed(job, image))
            job.failed.connect(lambda error: self.background_failed(job, error))
            job.progress.connect(lambda text: self.background_progress(job, text))
            self.statusBar().showMessage("Preparando el modelo local… La primera vez descarga unos 176 MB; necesitas conexión.")
            job.start()
        self.refresh()

    def background_progress(self, job: WhiteBackgroundJob, text: str):
        if job is self._background_job:
            self.statusBar().showMessage(text)

    def background_completed(self, job: WhiteBackgroundJob, image: QImage):
        if job is self._background_job:
            self._background_job = None
            self._white_image = image
            self.crop_view.image = image
            self.statusBar().showMessage("Fondo blanco aplicado. Revisa el pelo y los bordes antes de imprimir.", 12000)
            self.refresh()

    def background_failed(self, job: WhiteBackgroundJob, error: str):
        if job is not self._background_job:
            return
        self._background_job = None
        with QSignalBlocker(self.white_background):
            self.white_background.setChecked(False)
        self.crop_view.image = self._original_image
        self.refresh()
        self.statusBar().showMessage("No se pudo convertir el fondo. Se conserva la foto original.", 12000)
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle("No se pudo convertir el fondo")
        message.setText("La foto original está intacta. Puedes volver a marcar «Fondo blanco automático» para reintentar.")
        message.setInformativeText("Si es la primera vez, comprueba la conexión: hay que descargar el modelo antes de trabajar sin Internet.")
        message.setDetailedText(error)
        message.exec()

    def closeEvent(self, event):
        self.cancel_background()
        for job in self.findChildren(WhiteBackgroundJob):
            job.cancel()
            job.waitForFinished(1000)
        super().closeEvent(event)

    def change_zoom(self, value: int):
        self.crop_view.zoom = value / 100
        self.refresh()

    def apply_preset(self):
        dimensions = self.preset.currentData()
        if dimensions is not None:
            with QSignalBlocker(self.photo_width), QSignalBlocker(self.photo_height):
                self.photo_width.setValue(dimensions[0])
                self.photo_height.setValue(dimensions[1])
        self.refresh()

    def dimensions_changed(self):
        dimensions = (self.photo_width.value(), self.photo_height.value())
        index = next((i for i in range(self.preset.count()) if self.preset.itemData(i) == dimensions), 3)
        with QSignalBlocker(self.preset):
            self.preset.setCurrentIndex(index)
        self.refresh()

    def change_page(self):
        self.preview.page = self.page_selector.value() - 1
        self.preview.update()

    def refresh(self):
        settings = self.settings()
        self.crop_view.photo_size = (settings.width, settings.height)
        self.crop_view.update()
        crop = self.crop_view.source_rect()
        try:
            layout = make_layout(settings, self.paper_size, self.minimum_margins)
        except ValueError as error:
            self.current_layout = None
            self.preview.layout_data = None
            self.preview.update()
            self.print_button.setEnabled(False)
            self.summary.setText(str(error))
            self.summary.setStyleSheet("color: #a52e2e;")
            return
        self.current_layout = layout
        self.preview.layout_data = layout
        self.preview.image = self.crop_view.image
        self.preview.crop = crop
        with QSignalBlocker(self.page_selector):
            self.page_selector.setRange(1, layout.page_count)
            self.page_selector.setSuffix(f" de {layout.page_count}")
            self.page_selector.setEnabled(layout.page_count > 1)
        self.change_page()
        self.print_button.setEnabled(crop is not None and self._background_job is None)
        self.paper_label.setText(f"DIN A4 · {layout.paper_width:g} × {layout.paper_height:g} mm")
        text = f"{settings.copies} fotos de {settings.width:g} × {settings.height:g} mm · {layout.page_count} hoja(s)"
        if crop is not None:
            dpi = min(crop.width / settings.width, crop.height / settings.height) * 25.4
            if dpi < 200:
                text += f"\nResolución baja ({dpi:.0f} ppp): la foto puede verse pixelada."
        self.summary.setStyleSheet("color: #22382d;")
        self.summary.setText(text)

    def print_photos(self):
        if self._background_job is not None:
            QMessageBox.information(self, "Fondo blanco en proceso", "Espera a que termine o desmarca «Fondo blanco automático» para imprimir el original.")
            return
        crop = self.crop_view.source_rect()
        if self.current_layout is None or crop is None:
            QMessageBox.information(self, "Antes de imprimir", "Elige una foto y unas medidas que quepan en A4.")
            return
        dialog = QPrintDialog(self.printer, self)
        dialog.setWindowTitle("Imprimir fotos de carnet")
        dialog.setOption(QPrintDialog.PrintDialogOption.PrintSelection, False)
        dialog.setOption(QPrintDialog.PrintDialogOption.PrintCurrentPage, False)
        dialog.setOption(QPrintDialog.PrintDialogOption.PrintPageRange, True)
        dialog.setOption(QPrintDialog.PrintDialogOption.PrintShowPageSize, True)
        dialog.setMinMax(1, self.current_layout.page_count)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            layout = printer_layout(self.printer, self.settings())
            changed = layout != self.current_layout
            self.paper_size = (layout.paper_width, layout.paper_height)
            self.minimum_margins = printer_margins(self.printer)
            self.refresh()
            if changed:
                answer = QMessageBox.question(
                    self, "La distribución ha cambiado",
                    "Los márgenes o la orientación de la impresora cambian la distribución.\n"
                    "La vista previa ya está actualizada. ¿Imprimir así?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
            print_document(self.printer, self.crop_view.image, crop, layout)
        except (ValueError, PrintError) as error:
            QMessageBox.warning(self, "No se pudo imprimir", str(error))
            return
        self.statusBar().showMessage("Trabajo enviado. Puedes comprobarlo en la cola de impresión.", 12000)
