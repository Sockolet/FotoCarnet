"""Worker local: recibe un PNG por stdin y devuelve otro PNG por stdout."""

import sys
from contextlib import redirect_stdout
from io import BytesIO

from PIL import Image, ImageChops

MODEL = "u2net_human_seg"
PROCESSING_MARKER = "FOTOCARNET_PROCESSING"


def composite_on_white(image: Image.Image, mask: Image.Image) -> Image.Image:
    if mask.size != image.size:
        raise ValueError("La máscara no coincide con el tamaño de la foto.")
    alpha = ImageChops.multiply(mask.convert("L"), image.convert("RGBA").getchannel("A"))
    if alpha.getextrema()[1] < 128:
        raise ValueError("No se ha detectado una persona con suficiente claridad. Prueba otra foto.")
    result = Image.composite(image.convert("RGB"), Image.new("RGB", image.size, "white"), alpha)
    if "icc_profile" in image.info:
        result.info["icc_profile"] = image.info["icc_profile"]
    return result


def make_background_white(image: Image.Image) -> Image.Image:
    from rembg import new_session, remove

    session = new_session(MODEL, providers=["CPUExecutionProvider"])
    print(PROCESSING_MARKER, file=sys.stderr, flush=True)
    mask = remove(image, session=session, only_mask=True)
    if not isinstance(mask, Image.Image):
        raise TypeError("El modelo no ha devuelto una máscara de imagen.")
    return composite_on_white(image, mask)


def main() -> None:
    with Image.open(BytesIO(sys.stdin.buffer.read())) as image:
        # Las librerías pueden escribir mensajes; stdout se reserva para el PNG.
        with redirect_stdout(sys.stderr):
            result = make_background_white(image)
        result.save(sys.stdout.buffer, format="PNG")


if __name__ == "__main__":
    main()
