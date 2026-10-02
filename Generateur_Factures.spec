# -*- mode: python ; coding: utf-8 -*-
import os

# Icône de l'exe (et donc des raccourcis) et de la fenêtre : app/icon.ico si présent.
ICON = 'app/icon.ico' if os.path.exists('app/icon.ico') else None
datas = [('app/Azure-ttk-theme', 'Azure-ttk-theme')]
if ICON:
    datas.append((ICON, '.'))

a = Analysis(
    ['app\\generateur de facture.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Generateur_Factures',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)
