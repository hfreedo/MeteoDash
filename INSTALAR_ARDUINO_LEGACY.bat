@echo off
chcp 65001 >nul
title Arduino IDE Legacy / Drivers
cd /d "%~dp0\.."

echo.
echo ==========================================
echo   ARDUINO IDE LEGACY / DRIVERS
echo ==========================================
echo.
echo Usa esta opcion solo si el Arduino no aparece como puerto COM.
echo.

set "INSTALLER="

for %%F in (
    "instaladores\arduino-*.exe"
    "instaladores\Arduino*.exe"
    "instaladores\arduino-*.msi"
    "instaladores\Arduino*.msi"
) do (
    if not defined INSTALLER if exist "%%~F" set "INSTALLER=%%~F"
)

if not defined INSTALLER (
    echo No se encontro el instalador de Arduino IDE Legacy.
    echo.
    echo Copia el instalador dentro de la carpeta:
    echo instaladores
    echo.
    echo Nombres aceptados:
    echo - arduino-*.exe
    echo - Arduino*.exe
    echo - arduino-*.msi
    echo - Arduino*.msi
    echo.
    start "" "instaladores"
    pause
    exit /b 1
)

echo Instalador encontrado:
echo %INSTALLER%
echo.
echo Se abrira el instalador. Si Windows pide permisos, acepta.
echo Durante la instalacion acepta los drivers USB de Arduino.
echo.
pause
start "" "%INSTALLER%"

