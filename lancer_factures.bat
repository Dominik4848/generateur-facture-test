@echo off
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

start "" pythonw "%SCRIPT_DIR%generateur de facture.py"

endlocal
exit

