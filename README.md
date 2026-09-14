# FotoCarnet

El propósito de **FotoCarnet** es **facilitar la impresión a tamaño real de fotos de carnet**.

Una aplicación de escritorio pequeña: eliges una foto, defines sus medidas y el número de copias, y las imprimes agrupadas en una esquina del A4 para aprovechar el resto del papel. Sin cuentas, navegador ni subida de imágenes.

## Instalación y ejecución

Elige tu sistema: [Linux](#linux) · [Windows](#windows) · [macOS](#macos).

Los pasos instalan la aplicación desde su código fuente. Usaremos [uv](https://docs.astral.sh/uv/getting-started/installation/) para descargar **Python 3.13** y preparar `.venv`, una carpeta con las dependencias de FotoCarnet separadas del resto del sistema. **No necesitas instalar Python a mano ni activar un entorno virtual.**

Necesitas conexión para la instalación inicial y para descargar el modelo la primera vez que uses el fondo blanco automático. No necesitas una cuenta de GitHub ni una tarjeta gráfica dedicada. Para imprimir en papel, configura antes tu impresora en los ajustes de tu sistema.

### Compatibilidad de esta guía

| Sistema | Equipo y versión |
| --- | --- |
| Linux | Escritorio de 64 bits. En Intel/AMD, Ubuntu 22.04+ o Debian 12+ son ejemplos adecuados; en ARM64, Ubuntu 24.04+. |
| Windows | Windows 10 u 11 de 64 bits en un equipo Intel/AMD (x64). |
| macOS | macOS 14 Sonoma o posterior en un Mac con Apple Silicon (M1, M2, M3, etc.). |

Estos límites tienen en cuenta las versiones fijadas en [`uv.lock`](uv.lock). En otras distribuciones Linux se necesita glibc, una biblioteca del sistema, 2.34+ en x64 o 2.39+ en ARM64. **Mac Intel y Windows ARM64 no disponen de todas las dependencias precompiladas de esta versión y no están cubiertos por estos pasos.**

La interfaz y la impresión se han utilizado en Linux. Las instrucciones de Windows y macOS se basan en sus herramientas de instalación y en las dependencias disponibles; todavía no se ha comprobado su ejecución en esos sistemas.

### Linux

Los comandos de paquetes del primer paso son para **Ubuntu o Debian**. En otras distribuciones, instala sus equivalentes con el gestor de paquetes correspondiente; el resto de los pasos es igual. Necesitas una sesión de escritorio, no únicamente una terminal remota sin interfaz gráfica.

1. **Abre una terminal e instala Git, curl y las bibliotecas gráficas.** Git descargará el proyecto y curl, el instalador de uv. `sudo` puede pedir la contraseña de tu usuario:

   ```sh
   sudo apt update
   sudo apt install git curl libegl1 libgl1 libopengl0 \
     libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxkbcommon-x11-0
   ```

2. **Instala uv** con su instalador oficial:

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Cierra y vuelve a abrir la terminal.** Comprueba que los dos comandos muestran un número de versión:

   ```sh
   git --version
   uv --version
   ```

4. **Descarga FotoCarnet en tu carpeta personal y entra en el proyecto:**

   ```sh
   cd ~
   git clone https://github.com/Sockolet/FotoCarnet.git
   cd FotoCarnet
   ```

5. **Instala Python y las dependencias de la aplicación.** Espera a que ambos comandos terminen; la primera descarga puede tardar varios minutos:

   ```sh
   uv python install 3.13
   uv sync --locked --python 3.13
   ```

6. **Abre la aplicación.** Estos son también los comandos para abrirla otro día, sin repetir la instalación:

   ```sh
   cd ~/FotoCarnet
   ./iniciar.sh
   ```

### Windows

Usa **PowerShell**, disponible en el menú Inicio o en Windows Terminal. No hace falta usar WSL ni Git Bash.

1. **Instala Git y uv** con WinGet. Acepta los permisos que soliciten sus instaladores:

   ```powershell
   winget install --id Git.Git -e --source winget
   winget install --id astral-sh.uv -e --source winget
   ```

   Si `winget` no se reconoce, instala o actualiza **Instalador de aplicación** siguiendo la [guía oficial de WinGet](https://learn.microsoft.com/windows/package-manager/winget/), abre otra ventana de PowerShell y vuelve a ejecutar los comandos.

2. **Instala el runtime de Visual C++ para x64**, necesario para ONNX Runtime, el motor del fondo blanco. Descarga la versión **X64** desde la [página oficial de Microsoft](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist), abre el instalador y sigue sus pasos. Si ya tienes una versión compatible instalada, no necesitas reinstalarla.

3. **Cierra y vuelve a abrir PowerShell** y comprueba que aparecen los números de versión:

   ```powershell
   git --version
   uv --version
   ```

4. **Descarga FotoCarnet en tu carpeta de usuario y entra en el proyecto:**

   ```powershell
   cd $HOME
   git clone https://github.com/Sockolet/FotoCarnet.git
   cd FotoCarnet
   ```

5. **Instala Python y las dependencias** y espera a que terminen las descargas:

   ```powershell
   uv python install 3.13
   uv sync --locked --python 3.13
   ```

6. **Abre la aplicación.** Repite estos comandos cuando quieras volver a usarla:

   ```powershell
   cd "$HOME\FotoCarnet"
   uv run --locked python -m fotocarnet
   ```

   En PowerShell no uses `./iniciar.sh`: ese lanzador es para shells de Unix. Tampoco necesitas ejecutar `Activate.ps1` ni cambiar la política de ejecución de PowerShell.

### macOS

Estos pasos son para **Apple Silicon con macOS 14 o posterior**. Puedes consultar el chip y la versión del sistema en el menú Apple → **Acerca de este Mac**. Usa Terminal de forma nativa, no bajo Rosetta.

1. **Abre Terminal**, en Aplicaciones → Utilidades, e instala las herramientas de línea de comandos de Apple, que incluyen Git:

   ```sh
   xcode-select --install
   ```

   Completa la instalación en la ventana que se abra y espera a que termine. Si las herramientas ya están instaladas, continúa con el siguiente paso.

2. **Instala uv** con su instalador oficial:

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Cierra y vuelve a abrir Terminal** y comprueba que ambos comandos muestran una versión:

   ```sh
   git --version
   uv --version
   ```

4. **Descarga FotoCarnet en tu carpeta personal y entra en el proyecto:**

   ```sh
   cd ~
   git clone https://github.com/Sockolet/FotoCarnet.git
   cd FotoCarnet
   ```

5. **Instala Python y las dependencias** y espera a que finalice la descarga:

   ```sh
   uv python install 3.13
   uv sync --locked --python 3.13
   ```

6. **Abre la aplicación.** Usa estos mismos comandos para volver a abrirla otro día:

   ```sh
   cd ~/FotoCarnet
   uv run --locked python -m fotocarnet
   ```

### Después de instalar

Los pasos 1–5 solo se hacen la primera vez. Después basta con el paso 6 de tu sistema. Mantén la terminal abierta mientras usas la aplicación y cierra la ventana de FotoCarnet al terminar.

Si ya tenías el proyecto descargado, omite `git clone` y usa tu carpeta existente. Las instrucciones anteriores lo guardan en `FotoCarnet` dentro de tu carpeta personal; si lo has guardado en otro sitio, cambia la ruta de `cd` por la tuya.

Puedes seleccionar una imagen con **Elegir foto…**, o pasar su ruta entre comillas al arrancar:

```sh
uv run --locked python -m fotocarnet "photos/foto.jpg"
```

En ese ejemplo, `photos/foto.jpg` debe ser una foto existente dentro del proyecto; puedes sustituirlo por la ruta de tu imagen.

### Si no se abre

| Problema | Qué hacer |
| --- | --- |
| `uv` o `git` no se reconoce | Cierra y abre otra terminal después de instalarlo. Si continúa, revisa la instalación de esa herramienta antes de seguir. |
| No se encuentra `pyproject.toml` o el módulo `fotocarnet` | Entra con `cd` en la carpeta del proyecto, la que contiene este README, y vuelve a ejecutar el comando. |
| Linux: error de Qt, `xcb` o biblioteca gráfica ausente | Comprueba que instalaste los paquetes del paso 1 y que estás en una sesión de escritorio. En otras distribuciones, instala sus bibliotecas equivalentes. |
| Windows: error de carga de una DLL de ONNX Runtime | Instala o actualiza el runtime de Visual C++ **X64** del paso 2 y vuelve a abrir la app. |
| Linux: `Permission denied` al ejecutar el lanzador | Desde la carpeta del proyecto, ejecuta `sh iniciar.sh`. Puede ocurrir si descargaste un ZIP en lugar de clonar con Git. |
| No hay una distribución compatible de una dependencia | Revisa la tabla de compatibilidad y usa Python 3.13 con `uv sync --locked --python 3.13`; no cambies las versiones de las dependencias al azar. |

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

En Linux/macOS:

```sh
uv sync --locked
QT_QPA_PLATFORM=offscreen uv run --locked python -m unittest discover -v
```

En PowerShell:

```powershell
uv sync --locked
$env:QT_QPA_PLATFORM = "offscreen"
uv run --locked python -m unittest discover -v
Remove-Item Env:QT_QPA_PLATFORM
```

`fotocarnet/layout.py` calcula medidas, encuadre, esquinas y hojas sin depender de Qt. `printing.py` comparte el dibujo de las fotos con la vista previa y convierte milímetros a puntos del dispositivo. `app.py` contiene la interfaz. `background_job.py` ejecuta el modelo en un proceso cancelable; `background.py` recibe y devuelve la imagen por tuberías, sin archivos de fotos temporales. Las pruebas usan `unittest` y las dependencias de la aplicación; no descargan el modelo ni necesitan red.
