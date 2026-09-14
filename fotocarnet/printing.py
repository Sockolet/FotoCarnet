from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter
from PySide6.QtPrintSupport import QPrinter

from fotocarnet.layout import Layout, Margins, Rect, Settings, make_layout


class PrintError(RuntimeError):
    pass


def new_printer() -> QPrinter:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setDocName("FotoCarnet")
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setColorMode(QPrinter.ColorMode.Color)
    printer.setDuplex(QPrinter.DuplexMode.DuplexNone)
    return printer


def printer_margins(printer: QPrinter) -> Margins:
    page = printer.pageLayout()
    page.setUnits(QPageLayout.Unit.Millimeter)
    hardware = page.minimumMargins()
    selected = page.margins()
    return Margins(
        max(hardware.left(), selected.left()),
        max(hardware.top(), selected.top()),
        max(hardware.right(), selected.right()),
        max(hardware.bottom(), selected.bottom()),
    )


def printer_layout(printer: QPrinter, settings: Settings) -> Layout:
    size = printer.pageLayout().fullRect(QPageLayout.Unit.Millimeter)
    if any(abs(actual - expected) > 0.5 for actual, expected in zip(sorted((size.width(), size.height())), (210, 297))):
        raise ValueError("Selecciona papel DIN A4 en las propiedades de impresión. No se ha impreso nada.")
    return make_layout(settings, (size.width(), size.height()), printer_margins(printer))


def pages_to_print(printer: QPrinter, layout: Layout) -> tuple[int, ...]:
    if printer.printRange() == QPrinter.PrintRange.PageRange:
        start, end = printer.fromPage(), printer.toPage()
        if not 1 <= start <= end <= layout.page_count:
            raise ValueError(f"El intervalo de impresión debe estar entre 1 y {layout.page_count}.")
        pages = list(range(start - 1, end))
    elif printer.printRange() == QPrinter.PrintRange.AllPages:
        pages = list(range(layout.page_count))
    else:
        raise ValueError("Selecciona todas las páginas o un intervalo de páginas.")
    if printer.pageOrder() == QPrinter.PageOrder.LastPageFirst:
        pages.reverse()
    if not printer.supportsMultipleCopies():
        copies = printer.copyCount()
        pages = pages * copies if printer.collateCopies() else [page for page in pages for _ in range(copies)]
    return tuple(pages)


def draw_photos(painter: QPainter, image: QImage, crop: Rect, positions: tuple[Rect, ...]) -> None:
    source = QRectF(crop.x, crop.y, crop.width, crop.height)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    for rect in positions:
        painter.drawImage(QRectF(rect.x, rect.y, rect.width, rect.height), image, source)


def print_document(printer: QPrinter, image: QImage, crop: Rect, layout: Layout) -> None:
    if image.isNull():
        raise ValueError("Elige una foto antes de imprimir.")
    pages = pages_to_print(printer, layout)
    if not pages:
        raise ValueError("No hay hojas seleccionadas para imprimir.")

    # El origen es el borde físico del papel; los márgenes ya están en el layout.
    printer.setFullPage(True)
    painter = QPainter()
    if not painter.begin(printer):
        raise PrintError("No se pudo iniciar la impresión. Comprueba la impresora o la ruta del PDF.")
    completed = False
    try:
        for index, page in enumerate(pages):
            if index and not printer.newPage():
                raise PrintError("No se pudo crear la siguiente hoja. El trabajo puede estar incompleto.")
            painter.resetTransform()
            painter.scale(printer.logicalDpiX() / 25.4, printer.logicalDpiY() / 25.4)
            draw_photos(painter, image, crop, layout.positions(page))
        completed = True
    finally:
        if not completed:
            printer.abort()
        ended = painter.end()
    if not ended or printer.printerState() in (QPrinter.PrinterState.Error, QPrinter.PrinterState.Aborted):
        raise PrintError("La impresión no se completó. Comprueba la cola de impresión.")
