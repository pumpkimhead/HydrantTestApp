@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv-build\Scripts\python.exe" (
    py -m venv .venv-build
    if errorlevel 1 goto failed
)

set "BUILD_PYTHON=.venv-build\Scripts\python.exe"
"%BUILD_PYTHON%" -m pip install -r requirements-build.txt
if errorlevel 1 goto failed

"%BUILD_PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed --name HydrantTestApp --icon "icon-hydrant-circular.ico" --add-data "logo.png:." --add-data "icon-hydrant-circular.png:." --add-data "icon-hydrant-circular.ico:." hydrant_app.py
if errorlevel 1 goto failed

echo.
echo Build completed: dist\HydrantTestApp.exe
pause
exit /b 0

:failed
echo.
echo Build failed. See the error above.
pause
exit /b 1
