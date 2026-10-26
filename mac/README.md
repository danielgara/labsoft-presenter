# Presenter para macOS

`Presenter-macOS-arm64.dmg` es el archivo para descargar. Al abrirlo aparece `Presenter.app`: arrástrala a **Aplicaciones**.

Sirve en un Mac con chip Apple (M1, M2, M3, M4 o posterior) y macOS 11 o posterior: Big Sur, Monterey, Ventura, Sonoma, Sequoia o Tahoe. No abre en un Mac con procesador Intel.

## Instalar

1. Abre `Presenter-macOS-arm64.dmg`.
2. Arrastra `Presenter.app` a **Aplicaciones**.
3. Expulsa el dmg. A partir de ahí abre la app desde Aplicaciones, no desde el disco.

## Abrirla la primera vez

La app no está firmada por Apple. No la abras con doble clic: macOS la bloquea.

1. Haz clic derecho en `Presenter.app` y elige **Abrir**.
2. En el aviso, pulsa **Abrir** otra vez.

Si macOS dice que está dañada o que no se puede abrir, quita la marca de descarga y vuelve a abrirla con clic derecho:

```bash
xattr -dr com.apple.quarantine /Applications/Presenter.app
```

## Permisos

Presenter necesita dos permisos. Sin ellos se abre la barra, pero faltan atajos o el zoom. El permiso tiene que ser para **Presenter**, no para Terminal ni para el navegador.

Ábrela una vez antes de buscarla en Ajustes. Si no ha arrancado, no aparece en la lista.

En la guía de la app (el icono **?**) están **Permitir atajos** y **Permitir captura**. Esos botones abren el aviso del sistema. También puedes ir a mano, como sigue.

### Accesibilidad

Hace falta para los atajos (⌃⌥H, ⌃⌥L, ⌃⌥Z y el resto) y para enmarcar sin salir de la diapositiva.

En macOS 13 o posterior:

1. Abre **Ajustes del Sistema**.
2. Entra en **Privacidad y seguridad** → **Accesibilidad**.
3. Activa el interruptor de **Presenter**. Si pide tu contraseña, escríbela.

En macOS 11 o 12 la ruta es **Preferencias del Sistema** → **Seguridad y privacidad** → **Privacidad** → **Accesibilidad**. Pulsa el candado, escribe la contraseña y marca **Presenter**.

### Grabación de pantalla

Hace falta para el zoom. Sin este permiso el zoom sale negro.

En macOS 14 o posterior el ajuste se llama **Grabación de pantalla y audio del sistema**. En macOS 11, 12 y 13 se llama **Grabación de pantalla**. Está en el mismo sitio que Accesibilidad: **Privacidad y seguridad** (o **Privacidad**, en macOS 11 y 12).

1. Activa **Presenter** en esa lista.
2. Cierra Presenter por completo. El zoom no ve el permiso hasta el siguiente arranque.
3. Ábrela de nuevo.

Para cerrarla usa **Salir**, en la barra, o **Salir de Presenter**, en el icono de la barra de menús. Ocultar la barra no sale de la app.

## Si un permiso no responde

- Apaga el interruptor de Presenter, enciéndelo otra vez, sal de la app y ábrela.
- Si hay dos entradas llamadas Presenter, deja solo la de **Aplicaciones** y borra la otra con el botón **−**.
- Vuelve a conceder el permiso si moviste o reemplazaste `Presenter.app`.
