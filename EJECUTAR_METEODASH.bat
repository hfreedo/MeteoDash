@echo off
chcp 65001 >nul
title MeteoDash
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo MeteoDash todavia no esta preparado.
    echo Ejecuta primero el acceso directo 1 - Instalar MeteoDash
    echo.
    pause
    exit /b 1
)

if not exist "launcher_gui.py" (
    echo.
    echo ERROR: No se encontro launcher_gui.py
    echo Verifica que estes ejecutando este archivo desde la carpeta principal.
    echo.
    pause
    exit /b 1
)

echo.
echo Abriendo panel de MeteoDash...
echo.
".venv\Scripts\python.exe" "launcher_gui.py"

if errorlevel 1 (
    echo.
    echo MeteoDash se cerro con un error.
    echo Si el problema continua, vuelve a ejecutar 1 - Instalar MeteoDash
    echo.
    pause
)
