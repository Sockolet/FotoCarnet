# FotoCarnet

El propósito de **FotoCarnet** es **facilitar la impresión a tamaño real de fotos de carnet**.

Una aplicación de escritorio pequeña: eliges una foto, defines sus medidas y el número de copias, y las imprimes agrupadas en una esquina del A4 para aprovechar el resto del papel. Sin cuentas, navegador ni subida de imágenes.

## Abrir

Con [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado:

```sh
./iniciar.sh
```

La primera ejecución instala las dependencias en `.venv`; las siguientes reutilizan ese entorno. También puedes pasar una imagen: `./iniciar.sh /ruta/foto.jpg`.

Alternativa con Python 3.11 o posterior y un entorno virtual: instala las dependencias indicadas en `pyproject.toml` y ejecuta `python -m fotocarnet` desde esta carpeta.

## Uso

1. **Elegir foto**. Arrastra la imagen y ajusta el zoom si necesitas encuadrarla. Se respeta su proporción y la orientación EXIF; el original no se modifica.
2. Ajusta **Fotos en total**, tamaño y esquina. El valor inicial es **26 mm de ancho × 32 mm de alto**, con seis fotos arriba a la izquierda. Hay otros tamaños y medidas personalizadas. Comprueba qué medidas exige tu trámite: la aplicación no certifica la validez de una foto oficial.
3. **Imprimir…** abre el diálogo de impresión de Qt: usa las impresoras del sistema y sus propiedades mediante CUPS en Linux; Qt usa el diálogo nativo en Windows/macOS. Puedes elegir impresora, papel, color, calidad, páginas y copias según lo que permita el controlador. En Linux también permite imprimir a PDF.

El margen mínimo inicial es 5 mm y la separación entre fotos, 2 mm. Puedes cambiarlos, incluso a cero, pero se respetan los márgenes que comunique la impresora. Si no caben todas las fotos, se crean más hojas **sin reducir su tamaño**; puedes ver cada hoja en la vista previa. La última también empieza en la esquina elegida.

### Fondo blanco automático

Marca **Fondo blanco automático** debajo del encuadre para separar a la persona y sustituir el fondo por blanco. El resultado aparece tanto en la vista previa como en las fotos impresas, conservando sus dimensiones, el zoom y el encuadre.

La primera vez se descarga un modelo de unos **176 MB**; después funciona sin Internet. Usa [rembg](https://github.com/danielgatis/rembg) con el modelo local **U²-Net de segmentación de personas** (`u2net_human_seg`) y CPU, no un servicio en la nube. El modelo se guarda en la caché de rembg (normalmente `~/.rembg/models/`, o bajo `XDG_DATA_HOME` si está configurado).

Puedes seguir ajustando las copias y el encuadre mientras trabaja. Desmarca la opción para cancelar o recuperar el original; si ya terminó, puedes alternar entre ambos sin procesar de nuevo. Abrir otra foto cancela la conversión anterior y empieza con la opción desactivada. La impresión se habilita al terminar, para no imprimir accidentalmente el fondo original.

**Revisa especialmente el pelo, las orejas y los bordes:** la separación automática no siempre es perfecta y puede recortar detalles de la silueta. Algunos trámites no permiten fondos retocados; comprueba sus requisitos. Si falla la descarga o la conversión, se informa del error y se mantiene el original.

### Para no perder el tamaño ni el papel

- En las propiedades del controlador usa **A4, escala 100 % / tamaño real y una página por cara**. Desactiva «ajustar al papel», impresión de folletos y ampliación automática sin bordes. La aplicación dibuja en milímetros, pero no puede impedir que un controlador vuelva a escalar el trabajo.
- «Fotos en total» cuenta las fotos repartidas entre hojas. Las «copias» del diálogo de impresión repiten las hojas del trabajo: déjalas en **1** si solo quieres la cantidad indicada en la aplicación.
- Los bordes de la vista previa no se imprimen. No hay títulos, pies ni marcas en el sobrante.
- Puedes cambiar la orientación a horizontal en el diálogo. Si los ajustes alteran la distribución, la aplicación actualiza la vista previa y pide confirmación antes de enviar el trabajo. Un papel distinto de A4 se rechaza, sin imprimir.
- El tamaño real depende también de la calibración de la impresora. Antes de gastar papel fotográfico, imprime una foto en papel normal y mídela con una regla.
- Aprovechar el sobrante no significa que sea seguro volver a alimentar la impresora con un folio recortado: sigue las indicaciones de su fabricante.

Las fotos se procesan en memoria. La aplicación no las guarda ni las envía a servicios externos; el destino que elijas (impresora, cola del sistema o PDF) recibe el trabajo de impresión.

## Desarrollo

```sh
uv sync --locked
QT_QPA_PLATFORM=offscreen uv run --locked python -m unittest discover -v
```

`fotocarnet/layout.py` calcula medidas, encuadre, esquinas y hojas sin depender de Qt. `printing.py` comparte el dibujo de las fotos con la vista previa y convierte milímetros a puntos del dispositivo. `app.py` contiene la interfaz. `background_job.py` ejecuta el modelo en un proceso cancelable; `background.py` recibe y devuelve la imagen por tuberías, sin archivos de fotos temporales. Las pruebas usan `unittest` y las dependencias de la aplicación; no descargan el modelo ni necesitan red.
