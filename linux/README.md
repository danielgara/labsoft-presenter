# Presenter para Linux

`Presenter-linux-x86_64` es para PCs de 64 bits (x86_64) con Ubuntu 22.04 o posterior, Debian 12, Fedora 36 o cualquier distribución con glibc 2.35 o más nueva.

Es un solo archivo. Dale permiso de ejecución y ábrelo:

```bash
chmod +x Presenter-linux-x86_64
./Presenter-linux-x86_64
```

También puedes marcar **Permitir ejecutar como programa** en las propiedades del archivo y abrirlo con doble clic. Cada vez que se abre, se descomprime en una carpeta temporal, así que tarda unos segundos en aparecer.

Los atajos globales y el zoom necesitan una sesión X11. En Ubuntu, elige **Ubuntu en Xorg** en la pantalla de inicio de sesión. En Wayland la barra, el dibujo y el resto siguen funcionando.

Algunos escritorios usan los mismos atajos y se adelantan a Presenter: en Ubuntu, Ctrl+Alt+T abre la terminal; en XFCE, Ctrl+Alt+D muestra el escritorio (minimiza la presentación) y Ctrl+Alt+L bloquea la pantalla; en KDE, Ctrl+Alt+L también bloquea la pantalla. Usa los botones de la barra para esas herramientas o quita esos atajos en la configuración del teclado del escritorio.
