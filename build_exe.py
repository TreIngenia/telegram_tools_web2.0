import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

def build_executable(icon_path=None, name="TelegramMediaDownloader", version="1.0.0", one_file=True):
    """
    Costruisce un file eseguibile (.exe) dell'applicazione usando PyInstaller.
    
    Args:
        icon_path: Percorso all'icona (.ico) da utilizzare
        name: Nome dell'applicazione
        version: Versione dell'applicazione
        one_file: Se True, crea un unico file .exe, altrimenti crea una cartella
    """
    print(f"Inizializzazione della build dell'eseguibile {name} v{version}...")
    
    # Verifica se PyInstaller è installato
    try:
        import PyInstaller
        print("PyInstaller trovato.")
    except ImportError:
        print("PyInstaller non trovato. Installazione in corso...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller installato con successo.")
    
    # Crea la cartella di build se non esiste
    build_dir = "build"
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
        print(f"Cartella '{build_dir}' creata.")
    
    # Verifica l'icona
    if icon_path:
        if not os.path.exists(icon_path):
            print(f"ATTENZIONE: L'icona specificata {icon_path} non esiste.")
            icon_exists = False
            icon_path = None
        else:
            icon_exists = True
            print(f"Utilizzo dell'icona: {icon_path}")
    else:
        icon_exists = False
        print("Nessuna icona specificata, verrà utilizzata l'icona di default.")
    
    # Parametri per PyInstaller
    app_name = name.replace(" ", "")
    
    # File da includere
    include_files = [
        ".env",  # File di configurazione
        "README.md",  # Documentazione
    ]
    
    # Cartelle da creare nel pacchetto
    directories = [
        "downloads",
        "private", 
        "archive"
    ]
    
    # Comandi PyInstaller
    pyinstaller_cmd = [
        "pyinstaller",
        "--name=" + app_name,
        "--windowed",  # Non mostrare la console
        "--clean",     # Pulisci i file temporanei
        "--noconfirm", # Non chiedere conferma per sovrascrivere
        f"--version-file={version_file(name, version)}" if os.name == 'nt' else "",
        "--distpath=" + build_dir,  # Directory di output
    ]
    
    # Aggiungi one-file o one-dir
    if one_file:
        pyinstaller_cmd.append("--onefile")
    else:
        pyinstaller_cmd.append("--onedir")
    
    # Aggiungi l'icona se specificata
    if icon_exists:
        pyinstaller_cmd.append("--icon=" + icon_path)
    
    # Aggiungi i dati aggiuntivi
    for file in include_files:
        if os.path.exists(file):
            pyinstaller_cmd.append(f"--add-data={file};.")
    
    # Aggiungi hidden imports necessari
    pyinstaller_cmd.extend([
        "--hidden-import=emoji",
        "--hidden-import=telethon",
        "--hidden-import=asyncio",
        "--hidden-import=PyQt5",
    ])
    
    # Aggiungi il file principale dell'applicazione
    pyinstaller_cmd.append("gui.py")
    
    # Rimuovi elementi vuoti dalla lista
    pyinstaller_cmd = [cmd for cmd in pyinstaller_cmd if cmd]
    
    # Mostra il comando che verrà eseguito
    print("\nEsecuzione del comando:")
    print(" ".join(pyinstaller_cmd))
    print("\nCompilazione in corso...")
    
    # Esegui PyInstaller
    subprocess.check_call(pyinstaller_cmd)
    
    # Percorso alla directory di distribuzione
    if one_file:
        dist_dir = build_dir
        exe_path = os.path.join(build_dir, app_name + ".exe")
        package_dir = os.path.join(build_dir, app_name)
        
        # Crea una cartella con il nome dell'app per contenere l'exe e i file aggiuntivi
        if not os.path.exists(package_dir):
            os.makedirs(package_dir)
        
        # Sposta l'eseguibile nella cartella
        if os.path.exists(exe_path):
            shutil.copy2(exe_path, package_dir)
            print(f"File eseguibile copiato in {package_dir}")
    else:
        package_dir = os.path.join(build_dir, app_name)
        if not os.path.exists(package_dir):
            print(f"ERRORE: La directory {package_dir} non è stata creata correttamente.")
            return
    
    # Crea cartelle necessarie
    for dir_name in directories:
        os.makedirs(os.path.join(package_dir, dir_name), exist_ok=True)
    
    # Crea un file .env di esempio se non esiste già
    env_example_path = os.path.join(package_dir, ".env.example")
    with open(env_example_path, "w", encoding="utf-8") as f:
        f.write("# Configura le tue API Telegram qui\n")
        f.write("API_ID=12345678\n")
        f.write("API_HASH=abcdef1234567890abcdef1234567890\n")
    
    # Crea un batch file per avviare l'applicazione (utile per la modalità one-dir)
    if not one_file:
        batch_path = os.path.join(package_dir, "avvia.bat")
        with open(batch_path, "w") as f:
            f.write(f"@echo off\n")
            f.write(f"start {app_name}.exe\n")
    
    print(f"\nBuild completata! Il pacchetto è disponibile in: {os.path.abspath(package_dir)}")
    print(f"\nPer utilizzare l'applicazione:")
    print(f"1. Copia il file '.env.example' in '.env' e inserisci le tue credenziali API Telegram")
    print(f"2. Avvia l'applicazione facendo doppio clic sul file '{app_name}.exe'")

def version_file(app_name, version):
    """
    Crea un file di versione temporaneo per l'eseguibile Windows.
    
    Args:
        app_name: Nome dell'applicazione
        version: Stringa di versione (es. "1.0.0")
    
    Returns:
        path: Percorso al file di versione creato
    """
    if os.name != 'nt':
        return None  # Solo per Windows
    
    import tempfile
    
    # Converti la versione in formato Windows (1.0.0.0)
    version_parts = version.split('.')
    while len(version_parts) < 4:
        version_parts.append('0')
    win_version = '.'.join(version_parts[:4])
    
    # Crea un file temporaneo per la versione
    version_path = os.path.join(tempfile.gettempdir(), f"version_{app_name.lower()}.txt")
    
    with open(version_path, 'w') as f:
        f.write(f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({win_version.replace('.', ', ')}),
    prodvers=({win_version.replace('.', ', ')}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u''),
           StringStruct(u'FileDescription', u'{app_name}'),
           StringStruct(u'FileVersion', u'{version}'),
           StringStruct(u'InternalName', u'{app_name}'),
           StringStruct(u'LegalCopyright', u'Copyright (c) 2025'),
           StringStruct(u'OriginalFilename', u'{app_name}.exe'),
           StringStruct(u'ProductName', u'{app_name}'),
           StringStruct(u'ProductVersion', u'{version}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
        """.strip())
    
    return version_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crea un file eseguibile dell'applicazione.")
    parser.add_argument('--icon', type=str, help='Percorso all\'icona (.ico) da utilizzare')
    parser.add_argument('--name', type=str, default="TelegramMediaDownloader", help='Nome dell\'applicazione')
    parser.add_argument('--version', type=str, default="1.0.0", help='Versione dell\'applicazione')
    parser.add_argument('--onedir', action='store_true', help='Crea una directory invece di un singolo file')
    
    args = parser.parse_args()
    build_executable(icon_path=args.icon, name=args.name, version=args.version, one_file=not args.onedir)