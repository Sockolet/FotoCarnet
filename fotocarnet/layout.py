from dataclasses import dataclass
from enum import Enum
from math import ceil, floor, isfinite


class Corner(Enum):
    TOP_LEFT = "Arriba a la izquierda"
    TOP_RIGHT = "Arriba a la derecha"
    BOTTOM_LEFT = "Abajo a la izquierda"
    BOTTOM_RIGHT = "Abajo a la derecha"


@dataclass(frozen=True)
class Margins:
    left: float = 0
    top: float = 0
    right: float = 0
    bottom: float = 0


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class Settings:
    width: float = 26
    height: float = 32
    copies: int = 6
    corner: Corner = Corner.TOP_LEFT
    margin: float = 5
    gap: float = 2


@dataclass(frozen=True)
class Layout:
    settings: Settings
    paper_width: float
    paper_height: float
    margins: Margins
    max_columns: int
    max_rows: int

    @property
    def capacity(self) -> int:
        return self.max_columns * self.max_rows

    @property
    def page_count(self) -> int:
        return ceil(self.settings.copies / self.capacity)

    def positions(self, page: int) -> tuple[Rect, ...]:
        if not 0 <= page < self.page_count:
            raise ValueError("La hoja solicitada no existe.")
        s = self.settings
        count = min(self.capacity, s.copies - page * self.capacity)

        def footprint(columns: int) -> tuple[float, float]:
            rows = ceil(count / columns)
            width = columns * s.width + (columns - 1) * s.gap
            height = rows * s.height + (rows - 1) * s.gap
            return width + height, width * height

        # Minimizar el perímetro agrupa las fotos junto a la esquina.
        columns = min(
            range(ceil(count / self.max_rows), min(count, self.max_columns) + 1),
            key=footprint,
        )
        right = s.corner in (Corner.TOP_RIGHT, Corner.BOTTOM_RIGHT)
        bottom = s.corner in (Corner.BOTTOM_LEFT, Corner.BOTTOM_RIGHT)
        positions = []
        for index in range(count):
            row, column = divmod(index, columns)
            x = column * (s.width + s.gap)
            y = row * (s.height + s.gap)
            x = self.paper_width - self.margins.right - s.width - x if right else self.margins.left + x
            y = self.paper_height - self.margins.bottom - s.height - y if bottom else self.margins.top + y
            positions.append(Rect(x, y, s.width, s.height))
        return tuple(positions)


def make_layout(
    settings: Settings,
    paper_size: tuple[float, float] = (210, 297),
    minimum_margins: Margins = Margins(),
) -> Layout:
    s = settings
    if any(not isfinite(n) or n <= 0 for n in (s.width, s.height, *paper_size)):
        raise ValueError("Las medidas de la foto y del papel deben ser positivas.")
    if not isinstance(s.copies, int) or isinstance(s.copies, bool) or s.copies < 1:
        raise ValueError("El número de fotos debe ser un entero mayor que cero.")
    if not isinstance(s.corner, Corner):
        raise ValueError("Selecciona una de las cuatro esquinas.")
    edges = (
        minimum_margins.left, minimum_margins.top,
        minimum_margins.right, minimum_margins.bottom,
    )
    if any(not isfinite(n) or n < 0 for n in (s.margin, s.gap, *edges)):
        raise ValueError("Los márgenes y la separación no pueden ser negativos.")
    margins = Margins(*(max(s.margin, edge) for edge in edges))
    usable_width = paper_size[0] - margins.left - margins.right
    usable_height = paper_size[1] - margins.top - margins.bottom
    columns = floor((usable_width + s.gap + 1e-8) / (s.width + s.gap))
    rows = floor((usable_height + s.gap + 1e-8) / (s.height + s.gap))
    if columns < 1 or rows < 1:
        raise ValueError("La foto no cabe en el papel con estos márgenes. Reduce el tamaño o el margen.")
    return Layout(s, *paper_size, margins, columns, rows)


def crop_rect(
    image_width: float,
    image_height: float,
    photo_width: float,
    photo_height: float,
    focus: tuple[float, float] = (0.5, 0.5),
    zoom: float = 1,
) -> Rect:
    if any(not isfinite(n) or n <= 0 for n in (image_width, image_height, photo_width, photo_height)):
        raise ValueError("La imagen y el encuadre deben tener medidas positivas.")
    if not isfinite(zoom) or zoom < 1 or any(not isfinite(n) or not 0 <= n <= 1 for n in focus):
        raise ValueError("El encuadre o el zoom no son válidos.")
    width = min(image_width, image_height * photo_width / photo_height) / zoom
    height = width * photo_height / photo_width
    return Rect(
        max(0, image_width - width) * focus[0],
        max(0, image_height - height) * focus[1],
        width,
        height,
    )
