@echo off
rem Installe (ou met a jour) le Generateur de factures depuis la derniere Release GitHub :
rem   - telecharge Generateur_Factures.exe dans Documents\Generateur de factures
rem   - cree le raccourci "Generateur de factures" sur le Bureau
rem La commande est identique a celle de l'option 2 du README.

tasklist /fi "imagename eq Generateur_Factures.exe" | find /i "Generateur_Factures.exe" >nul && (
    echo [ERREUR] Le Generateur de factures est ouvert : ferme-le puis relance ce script.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; $d=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Generateur de factures'; $exe=Join-Path $d 'Generateur_Factures.exe'; New-Item -ItemType Directory -Force $d | Out-Null; Invoke-WebRequest 'https://github.com/Dominik4848/generateur-facture-test/releases/latest/download/Generateur_Factures.exe' -OutFile ($exe + '.part') -UseBasicParsing; Move-Item -Force ($exe + '.part') $exe; Unblock-File $exe; $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Generateur de factures.lnk')); $s.TargetPath=$exe; $s.WorkingDirectory=$d; $s.IconLocation=$exe; $s.Save(); Write-Host ('Installe dans ' + $d + ' - raccourci cree sur le Bureau.')" || (
    echo.
    echo [ERREUR] L'installation a echoue, voir le message ci-dessus.
    pause
    exit /b 1
)
pause
