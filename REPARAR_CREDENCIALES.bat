@echo off
setlocal
chcp 65001 >nul
title Reparar Credenciales MeteoDash
cd /d "%~dp0\.."

echo.
echo ==========================================
echo   REPARAR CREDENCIALES METEODASH
echo ==========================================
echo.
echo Se restauraran las credenciales de demostracion:
echo Admin: admin / admin123
echo Visitante: visitante / visitante123
echo.

if not exist "backend" (
    echo ERROR: No se encontro la carpeta backend.
    echo.
    if /i not "%~1"=="/quiet" pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "$users = [ordered]@{" ^
    "  admin = [ordered]@{ username='admin'; password_hash='$2b$12$UFP5mq1k1Hk7JiEZjVKH/epaRYNBk5MHxj2CLEStmo/ooTboM.rUu'; role='admin'; name='Administrador' };" ^
    "  visitor = [ordered]@{ username='visitante'; password_hash='$2b$12$/uI0wzwOsRussReiTyc6I.DTBqCQvZdzazsCVE/.RJb1R3ZuNluF2'; role='visitor'; name='Visitante' }" ^
    "};" ^
    "$json = $users | ConvertTo-Json -Depth 4;" ^
    "$utf8NoBom = New-Object System.Text.UTF8Encoding($false);" ^
    "[System.IO.File]::WriteAllText((Resolve-Path 'backend\users.json'), $json, $utf8NoBom)"

if errorlevel 1 (
    echo ERROR: No se pudo actualizar backend\users.json
    echo.
    if /i not "%~1"=="/quiet" pause
    exit /b 1
)

echo Credenciales restauradas correctamente.
echo.
if /i not "%~1"=="/quiet" pause
exit /b 0
