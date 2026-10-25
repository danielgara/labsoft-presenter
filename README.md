# Presenter

Una capa ligera para presentar. Resalta un elemento, amplía la pantalla, escribe sobre una diapositiva o elige un estudiante al azar.

## Descargas

| Sistema | Archivo | Instrucciones |
| --- | --- | --- |
| macOS (Apple Silicon) | [Presenter-macOS-arm64.dmg](mac/Presenter-macOS-arm64.dmg) | [mac/README.md](mac/README.md) |
| Windows 10 y 11 (64 bits) | [Presenter.exe](windows/Presenter.exe) | [windows/README.md](windows/README.md) |
| Linux (x86_64) | [Presenter-linux-x86_64](linux/Presenter-linux-x86_64) | [linux/README.md](linux/README.md) |

La barra queda en la parte inferior de la pantalla. Arrastra el anillo dorado para moverla.

El código fuente está en la rama [`development`](../../tree/development).

## Permisos de macOS

La primera vez, macOS pide dos permisos para **Presenter**:

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
