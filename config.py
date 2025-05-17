import os
from dotenv import load_dotenv

# Caricamento delle variabili d'ambiente
load_dotenv()

# Credenziali Telegram
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')

# Directory
DOWNLOADS_DIR = "downloads"
TEMP_DIR = "private"
ARCHIVE_DIR = "archive"  # Directory per gli archivi completi dei gruppi

# File di configurazione
USER_GROUPS_FILE = "user_groups.json"
PHONE_NUMBERS_FILE = "phone_numbers.json"
LOCK_FILE = "running_instances.lock"  # File per gestire istanze multiple

# Impostazioni
VERBOSE = True
MAX_DOWNLOAD_RETRIES = 3
DOWNLOAD_RETRY_DELAY = 2  # secondi

# Creazione delle directory se non esistono
for directory in [DOWNLOADS_DIR, TEMP_DIR, ARCHIVE_DIR]:
    os.makedirs(directory, exist_ok=True)