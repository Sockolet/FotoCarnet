import argparse
import logging
import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from fotocarnet.app import MainWindow


def main() -> int:
    parser = argparse.ArgumentParser(description="Fotos de carnet en una esquina del A4.")
    parser.add_argument("foto", nargs="?", help="Imagen que se abrirá al iniciar")
    args = parser.parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("FotoCarnet")
    QLocale.setDefault(QLocale("es_ES"))
    translator = QTranslator(app)
    if translator.load("qtbase_es", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(translator)
    else:
        logging.warning("No se encontró la traducción española de los diálogos de Qt.")
    window = MainWindow()
    window.show()
    if args.foto:
        window.load_photo(args.foto)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
