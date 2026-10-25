# Presenter para macOS

`Presenter-macOS-arm64.dmg` es para Mac con Apple Silicon (M1 o posterior).

1. Abre el dmg y arrastra `Presenter.app` a la carpeta Aplicaciones.
2. La app no está firmada por Apple. La primera vez, haz clic derecho en `Presenter.app` y elige **Abrir**. Si macOS dice que está dañada, ejecuta:

   ```bash
   xattr -dr com.apple.quarantine /Applications/Presenter.app
   ```

3. Permite **Accesibilidad** y **Grabación de pantalla** para Presenter, ciérrala y ábrela de nuevo.
