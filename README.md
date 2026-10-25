# Presenter

Una capa ligera para presentar en macOS. Resalta un elemento, amplía la pantalla, escribe sobre una diapositiva o elige un estudiante al azar.

## Ejecutar

```bash
uv sync
uv run presenter
```

La barra queda en la parte inferior de la pantalla. Arrastra el anillo dorado para moverla.

## Aplicación de escritorio

Hay que empaquetar en el mismo sistema donde se va a usar.

En macOS, el comando crea `dist/Presenter.app`. Ábrela con doble clic o cópiala a Aplicaciones. Antes, genera el icono con `uv run python packaging/make_icon.py`. La primera vez, macOS pide Accesibilidad y Grabación de pantalla para **Presenter**.

En Windows, el mismo comando crea `dist/Presenter.exe`.

En Linux, crea un solo archivo, `dist/Presenter`. Dale permiso de ejecución si hace falta (`chmod +x dist/Presenter`) y ábrelo. Los atajos globales y la captura del zoom funcionan en X11; en Wayland el escritorio suele bloquearlos. El dibujo, la barra y el resto de la app siguen disponibles.

```bash
uv sync --group package
uv run pyinstaller presenter.spec --noconfirm
```

Para la descarga de macOS, mete la app en un dmg con un acceso a Aplicaciones:

```bash
mkdir -p build/dmg
ditto dist/Presenter.app build/dmg/Presenter.app
ln -sfn /Applications build/dmg/Applications
hdiutil create -volname Presenter -srcfolder build/dmg -ov -format UDZO -fs HFS+ mac/Presenter-macOS-arm64.dmg
```

## Permisos de macOS

Presenter necesita dos permisos. Si lo abres con `uv run`, macOS se los concede a la app que abre Python (Terminal, iTerm o Cursor). Si abres `Presenter.app`, se los concede a Presenter:

- **Accesibilidad** — atajos de teclado y enmarcar mientras sigues presentando.
- **Grabación de pantalla** — el zoom.

Si aparece un aviso, permítelo, cierra Presenter y ábrelo de nuevo.

## Atajos

| Acción | Atajo |
| --- | --- |
| Resaltar | ⌃⌥H |
| Láser | ⌃⌥L |
| Zoom | ⌃⌥Z |
| Dibujar | ⌃⌥D |
| Escribir | ⌃⌥T |
| Mostrar u ocultar herramientas | ⌃⌥P |
| Salir de la herramienta | Esc |
| Deshacer | ⌘Z |

En Windows y Linux, ⌃ es Ctrl, ⌥ es Alt y Deshacer es Ctrl+Z.

Al resaltar, pulsa **Marco** y arrastra alrededor de un elemento. Mantén ⌥ y arrastra para enmarcar sin salir de la diapositiva. Mantén ⌃ y desplázate, o usa + y −, para cambiar el foco de luz; la rueda sola sigue moviendo la diapositiva. En Zoom, desplázate o usa + y − para cambiar el aumento. Con varias pantallas, Zoom pide primero cuál ampliar y sigue al puntero solo en esa pantalla. Con el zoom activo, un doble clic pasa al lápiz y otro doble clic vuelve a mover.

La tinta y los marcos permanecen al salir de una herramienta. **Borrar** los quita. **Listo** o Esc da un paso atrás.

## Elegir al azar

El icono de laboratorio, en la barra, muestra las pruebas. Ahí están el dado y el tiempo.

El dado abre la fila del listado.

**Cargar lista** lee un archivo de texto con un nombre por renglón. Las líneas vacías se ignoran. La lista queda guardada con el nombre del archivo.

Al abrir Presenter de nuevo, el dado muestra esas listas. Pulsa una para usarla. La X roja con borde redondo, al inicio del botón, quita esa lista.

**Elegir** hace pasar varios nombres, frena y deja el elegido en dorado. No repite un nombre hasta que hayan salido todos.

La papelera junto al nombre lo quita solo en esta sesión. El archivo guardado no cambia.

**Tiempo** pide primero la pantalla, luego los minutos y los segundos. La cuenta atrás queda en esa pantalla. Pulsa el icono otra vez para quitarla.
