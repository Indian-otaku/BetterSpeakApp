# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('betterspeaklogo.jpg', '.'),
        ('config.py', '.'),
        ('get_model_result.py', '.'),
        ('main.py', '.'),
        ('main.spec', '.'),
        ('styles.css', '.'),
        ('syllable_counter.py', '.'),
        ('saved_recordings', 'saved_recordings'),
        ('saved_model', 'saved_model'),
        ('saved_model/interjection.ckpt', 'saved_model'),
        ('saved_model/prolongation.pth', 'saved_model'),
        ('saved_model/repetition.pth', 'saved_model'),
        ('saved_model/w2v2_architecture/config.json', 'saved_model/w2v2_architecture'),
        ('saved_model/w2v2_architecture/model.safetensors', 'saved_model/w2v2_architecture'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
splash = Splash(
    '.\\betterspeaklogo.ico',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=False,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['betterspeaklogo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    splash.binaries,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)
