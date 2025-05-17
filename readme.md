# Telegram Media Downloader

Un'applicazione moderna per il download e la gestione dei media da gruppi e canali Telegram, con interfaccia grafica.

## Caratteristiche

- 📱 **Gestione utenti**: Aggiungi e rimuovi account Telegram
- 👥 **Gestione gruppi**: Visualizza e interagisci con i tuoi gruppi e canali
- 📥 **Download archivi**: Scarica tutti i media da un gruppo o canale
- 🔄 **Monitoraggio**: Monitora uno o più gruppi in tempo reale
- 📊 **Istanze multiple**: Esegui più istanze contemporaneamente per operazioni diverse
- 🖥️ **Interfaccia grafica**: Interfaccia moderna e intuitiva

## Requisiti

- Python 3.7 o superiore
- Credenziali API Telegram (API_ID e API_HASH)

## Installazione

1. Clona il repository:
   ```
   git clone https://github.com/tuonome/telegram-media-downloader.git
   cd telegram-media-downloader
   ```

2. Installa le dipendenze:
   ```
   pip install -r requirements.txt
   ```

3. Crea un file `.env` nella directory principale con le tue credenziali API Telegram:
   ```
   API_ID=12345678
   API_HASH=abcdef1234567890abcdef1234567890
   ```

## Utilizzo

### Interfaccia grafica

Per avviare l'applicazione con l'interfaccia grafica:

```
python gui.py
```

### Versione a riga di comando

Per avviare l'applicazione a riga di comando:

```
python app.py
```

## Come ottenere le credenziali API Telegram

1. Vai su https://my.telegram.org/auth
2. Accedi con il tuo numero di telefono
3. Vai a "API development tools"
4. Crea una nuova applicazione
5. Copia l'API_ID e l'API_HASH nel file `.env`

## Creare un eseguibile (.exe)

Per creare un file eseguibile per Windows:

1. Installa PyInstaller:
   ```
   pip install pyinstaller
   ```

2. Esegui lo script di build:
   ```
   python build_exe.py

   python build_exe.py --icon "app_icon.ico" --name "Telegram Media Downloader" --version "1.0.0"

   ```

3. Troverai l'eseguibile nella cartella `build/TelegramMediaDownloader/`

## Struttura del progetto

- `app.py`: Applicazione principale a riga di comando
- `gui.py`: Interfaccia grafica
- `config.py`: Configurazione dell'applicazione
- `utils.py`: Funzioni di utilità
- `user_management.py`: Gestione degli utenti
- `group_management.py`: Gestione dei gruppi
- `media_handler.py`: Gestione e download dei media
- `event_handler.py`: Gestione degli eventi Telegram
- `multiinstance.py`: Gestione delle istanze multiple

## Struttura delle directory

- `downloads/`: Dove vengono salvati i media
  - `[utente]/`: Cartella per ogni utente dell'applicazione
    - `[gruppo]/`: Cartella per ogni gruppo
      - `images/`: Immagini
      - `videos/`: Video
      - `documents/`: Documenti
      - ecc.
- `private/`: File temporanei e private
- `archive/`: Archivi completi dei gruppi
  - `[utente]/`: Cartella per ogni utente dell'applicazione
    - `[gruppo]/`: Cartella per ogni gruppo archiviato

## Licenza

[MIT](LICENSE)