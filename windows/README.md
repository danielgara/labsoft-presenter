# Presenter para Windows

`Presenter.exe` es para Windows 10 y 11 de 64 bits. No necesita instalación: descárgalo y ábrelo con doble clic.

El ejecutable no está firmado. Si Windows muestra **Windows protegió su PC**, pulsa **Más información** y luego **Ejecutar de todas formas**.

Para generarlo de nuevo, en un PC con Windows:

```bash
uv sync --group package
uv run pyinstaller presenter.spec --noconfirm
```

El resultado queda en `dist/Presenter.exe`.
