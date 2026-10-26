# Presenter para Linux

`Presenter-linux-x86_64` es un solo archivo para PCs de 64 bits (x86_64).

Sirve en Ubuntu 22.04 o posterior, Debian 12, Fedora 36 o cualquier distribución con glibc 2.35 o más nueva. No es para ARM.

## Abrir

En la carpeta donde lo descargaste:

```bash
chmod +x Presenter-linux-x86_64
./Presenter-linux-x86_64
```

También puedes marcar **Permitir ejecutar como programa** en las propiedades del archivo y abrirlo con doble clic.

La primera vez tarda unos segundos: se descomprime en una carpeta temporal y luego aparece la barra.

## Zoom y atajos

Los atajos globales y el zoom necesitan una sesión **X11**. En Wayland el escritorio no deja capturar la pantalla ni leer esas teclas. La barra, el dibujo, el texto y el resto sí funcionan.

En Ubuntu, en la pantalla de inicio de sesión, elige **Ubuntu en Xorg** antes de entrar.

## Si un atajo abre otra cosa

Algunos escritorios usan las mismas teclas y se adelantan a Presenter:

| Escritorio | Teclas | Qué hace el sistema |
| --- | --- | --- |
| Ubuntu | Ctrl+Alt+T | Abre la terminal |
| XFCE | Ctrl+Alt+D | Muestra el escritorio y minimiza la presentación |
| XFCE y KDE | Ctrl+Alt+L | Bloquea la pantalla |

Para esas herramientas usa el botón de la barra, o quita el atajo en la configuración del teclado del escritorio. En Presenter, Ctrl es ⌃, Alt es ⌥ y Deshacer es Ctrl+Z.
