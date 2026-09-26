@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Please run setup.cmd first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -u run_all.py
popd
pause
