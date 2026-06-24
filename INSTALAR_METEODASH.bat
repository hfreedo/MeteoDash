@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Instalador MeteoDash
cd /d "%~dp0\.."

echo.
echo ==========================================
echo   INSTALADOR METEODASH
echo ==========================================
echo.
echo Este instalador prepara MeteoDash en esta carpeta.
echo Creara un entorno local .venv y no modificara el proyecto base.
echo.

if not exist "backend\requirements.txt" (
    echo ERROR: No se encontro backend\requirements.txt
    echo Verifica que este archivo este en la carpeta principal de MeteoDash.
    echo.
    pause
    exit /b 1
)

set "PYTHON_CMD="
call :find_python

if not defined PYTHON_CMD (
    echo Python no esta instalado o no fue detectado.
    echo.
    call :install_python
    call :find_python
)

if not defined PYTHON_CMD (
    echo.
    echo ERROR: No se pudo detectar Python automaticamente.
    echo.
    echo Solucion:
    echo 1. Abre la carpeta instaladores.
    echo 2. Ejecuta python-3.12.10-amd64.exe.
    echo 3. Marca "Add python.exe to PATH" si aparece.
    echo 4. Vuelve a abrir 1 - Instalar MeteoDash.
    echo.
    start "" "instaladores"
    pause
    exit /b 1
)

echo Python detectado:
%PYTHON_CMD% --version
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno local .venv...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo.
        echo No se pudo crear .venv en el primer intento.
        echo Limpiando entorno incompleto y reintentando...
        echo.
        if exist ".venv" rmdir /s /q ".venv"
        %PYTHON_CMD% -m venv .venv
        if errorlevel 1 (
            echo.
            echo ERROR: No se pudo crear el entorno .venv.
            echo Reinstala Python desde la carpeta instaladores y vuelve a intentar.
            echo.
            pause
            exit /b 1
        )
    )
) else (
    echo Entorno .venv ya existe. Se reutilizara.
)

echo.
echo Actualizando pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo actualizar pip.
    echo Revisa tu conexion a internet y vuelve a ejecutar este instalador.
    echo.
    pause
    exit /b 1
)

echo.
echo Instalando dependencias de MeteoDash...
".venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 (
    echo.
    echo ERROR: No se pudieron instalar las dependencias.
    echo Revisa tu conexion a internet y vuelve a ejecutar este instalador.
    echo.
    pause
    exit /b 1
)

echo.
echo Restaurando credenciales de demostracion...
call "soporte\REPARAR_CREDENCIALES.bat" /quiet
if errorlevel 1 (
    echo.
    echo ADVERTENCIA: No se pudieron restaurar las credenciales automaticamente.
    echo Puedes ejecutar 4 - Reparar Credenciales despues de la instalacion.
)

echo.
echo ==========================================
echo   INSTALACION COMPLETADA
echo ==========================================
echo.
echo Ahora abre el acceso directo 2 - Abrir MeteoDash
echo.
pause
exit /b 0

:find_python
set "PYTHON_CMD="

where py >nul 2>&1
if not errorlevel 1 (
    py -3 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
        exit /b 0
    )
)

where python >nul 2>&1
if not errorlevel 1 (
    python --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
        exit /b 0
    )
)

where python3 >nul 2>&1
if not errorlevel 1 (
    python3 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=python3"
        exit /b 0
    )
)

for /d %%D in (
    "%LocalAppData%\Programs\Python\Python*"
    "%ProgramFiles%\Python*"
    "%ProgramFiles(x86)%\Python*"
) do (
    if exist "%%~D\python.exe" (
        set "PYTHON_CMD="%%~D\python.exe""
        exit /b 0
    )
)

exit /b 0

:install_python
set "PYTHON_INSTALLER="

for %%F in (
    "instaladores\python-*-amd64.exe"
    "instaladores\python-*.exe"
    "instaladores\Python*.exe"
) do (
    if not defined PYTHON_INSTALLER if exist "%%~F" set "PYTHON_INSTALLER=%%~F"
)

if defined PYTHON_INSTALLER (
    echo Instalador local de Python encontrado:
    echo !PYTHON_INSTALLER!
    echo.
    echo Instalando Python para este usuario...
    echo Si Windows solicita permisos, acepta la instalacion.
    echo.
    start /wait "" "!PYTHON_INSTALLER!" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1 Include_tcltk=1 Include_test=0 SimpleInstall=1
    exit /b 0
)

where winget >nul 2>&1
if not errorlevel 1 (
    echo Intentando instalar Python 3 con winget...
    echo Si Windows solicita permisos, acepta la instalacion.
    echo.
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    exit /b 0
)

echo winget no esta disponible en esta computadora.
echo Intentando descargar Python oficial desde python.org...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "New-Item -ItemType Directory -Force -Path 'instaladores' | Out-Null;" ^
    "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile 'instaladores\python-3.12.10-amd64.exe'"

if exist "instaladores\python-3.12.10-amd64.exe" (
    set "PYTHON_INSTALLER=instaladores\python-3.12.10-amd64.exe"
    echo Descarga completada. Instalando Python...
    start /wait "" "!PYTHON_INSTALLER!" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_pip=1 Include_tcltk=1 Include_test=0 SimpleInstall=1
) else (
    echo No se pudo descargar Python automaticamente.
)

exit /b 0
