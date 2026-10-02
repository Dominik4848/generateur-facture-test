@echo off
setlocal
cd /d "%~dp0"

rem --- Python : "python" ou, a defaut, le lanceur "py"
set PY=python
%PY% --version >nul 2>&1 || set PY=py
%PY% --version >nul 2>&1 || (
    echo [ERREUR] Python est introuvable. Installe-le depuis le Software Center ou python.org,
    echo          en cochant "Add python.exe to PATH", puis relance ce script.
    pause
    exit /b 1
)

echo [1/3] Installation des dependances...
%PY% -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto :erreur

echo [2/3] Construction de l'executable...
tasklist /fi "imagename eq Generateur_Factures.exe" | find /i "Generateur_Factures.exe" >nul && (
    echo [ERREUR] Generateur_Factures.exe est ouvert : ferme-le puis relance ce script.
    pause
    exit /b 1
)
%PY% -m PyInstaller --noconfirm --log-level WARN Generateur_Factures.spec || goto :erreur

echo [3/3] Creation du raccourci sur le Bureau...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$exe = Join-Path (Resolve-Path 'dist') 'Generateur_Factures.exe';" ^
  "$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Generateur de factures.lnk';" ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk);" ^
  "$s.TargetPath = $exe; $s.WorkingDirectory = Split-Path $exe; $s.IconLocation = $exe;" ^
  "$s.Description = 'Generateur de documents de test'; $s.Save();" ^
  "Write-Host ('Raccourci cree : ' + $lnk)" || goto :erreur

echo.
echo Termine. Lance l'application depuis le raccourci "Generateur de factures" sur ton Bureau.
echo Les PDF sont crees dans le dossier dist\ (factures_sortie, z_caisse_sortie, rib_sortie).
pause
exit /b 0

:erreur
echo.
echo [ERREUR] L'installation a echoue, voir les messages ci-dessus.
pause
exit /b 1
