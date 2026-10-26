# Presenter

Una capa ligera para presentar. Resalta un elemento, amplía la pantalla, escribe sobre una diapositiva o elige un estudiante al azar.

La barra queda en la parte inferior. El anillo dorado, a la izquierda, la arrastra.

## Descargas

| Sistema | Archivo | Instrucciones |
| --- | --- | --- |
| macOS 11 o posterior, chip Apple (M1 o posterior) | [Presenter-macOS-arm64.dmg](mac/Presenter-macOS-arm64.dmg) | [mac/README.md](mac/README.md) |
| Windows 10 y 11 (64 bits) | [Presenter.exe](windows/Presenter.exe) | [windows/README.md](windows/README.md) |
| Linux (x86_64) | [Presenter-linux-x86_64](linux/Presenter-linux-x86_64) | [linux/README.md](linux/README.md) |

La primera vez cada sistema avisa. En Mac faltan los atajos o el zoom sale negro hasta dar los permisos. En Windows, SmartScreen puede bloquear el exe. En Linux, los atajos y el zoom necesitan X11. El paso a paso está en la guía de cada archivo.

El código fuente está en la rama [`development`](https://github.com/danielgara/labsoft-presenter/tree/development).

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

## Herramientas

**Resaltar** oscurece la pantalla y deja un foco de luz. **Marco**, o ⌥ y arrastrar, enmarca un elemento sin salir de la diapositiva. ⌃ y la rueda, o + y −, cambian el tamaño del foco. La rueda sola sigue moviendo la diapositiva.

**Zoom** pide la pantalla si hay más de una y sigue al puntero solo en esa. La rueda, o + y −, cambia el aumento. Un doble clic pasa al lápiz y otro doble clic vuelve a mover.

**Dibujar** y **Escribir** dejan tinta y texto sobre la diapositiva. Siguen ahí al salir de la herramienta. **Borrar** los quita. **Listo** o Esc da un paso atrás. ⌘Z deshace lo último.

## Pruebas

El matraz, en la barra, muestra las pruebas. Ahí están el dado y el tiempo.

**Dado.** **Cargar lista** lee un archivo de texto con un nombre por renglón. Las líneas vacías se ignoran. La lista queda guardada con el nombre del archivo. Al abrir Presenter de nuevo, el dado muestra esas listas: pulsa una para usarla. La X roja al inicio del botón quita esa lista.

**Elegir** hace pasar varios nombres, frena y deja el elegido en dorado. No repite un nombre hasta que hayan salido todos. La papelera junto al nombre lo quita solo en esta sesión. El archivo guardado no cambia.

**Tiempo** pide primero la pantalla, luego los minutos y los segundos. La cuenta atrás queda en esa pantalla. Pulsa el icono otra vez para quitarla.
