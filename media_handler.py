import os
import time
import asyncio
import mimetypes
import traceback
import shutil
import random
from datetime import datetime
from telethon import TelegramClient, utils

# Importa il session manager
from gui_session_manager import session_manager

from utils import log_error, retry_operation, sanitize_group_name, format_user_info, sanitize_username
from config import (
    API_ID, API_HASH, DOWNLOADS_DIR, TEMP_DIR, ARCHIVE_DIR,
    MAX_DOWNLOAD_RETRIES, DOWNLOAD_RETRY_DELAY, VERBOSE
)

def get_media_type(message):
    """Determina il tipo di media di un messaggio."""
    if message.photo:
        return "images"
    elif message.video:
        return "videos"
    elif message.audio:
        return "audio"
    elif message.voice:
        return "voice"
    elif message.document:
        return "documents"
    elif message.sticker:
        return "stickers"
    elif message.gif:
        return "gifs"
    else:
        return "others"

async def safe_download_media(message, file_path, retries=MAX_DOWNLOAD_RETRIES):
    """Scarica un media con tentativi multipli."""
    try:
        return await retry_operation(
            message.download_media,
            file=file_path,
            retries=retries,
            delay=DOWNLOAD_RETRY_DELAY
        )
    except Exception as e:
        log_error(f"Download fallito definitivamente: {e}")
        return None

async def download_media(message, group_name, app_nickname=None, base_dir=DOWNLOADS_DIR, sender_info=None):
    """Scarica il media da un messaggio e lo salva nella cartella appropriata."""
    media_type = get_media_type(message)
    if media_type == "others":
        if VERBOSE:
            print(f"⚠️ Media non supportato (ID: {message.id})")
        log_error(f"Media non supportato ID: {message.id}")
        return None

    # Prepara informazioni sull'utente
    if not sender_info:
        user_folder = "unknown_user"
        user_id = message.sender_id if hasattr(message, 'sender_id') else "unknown"
        sender_display = f"User_{user_id}"
    else:
        if sender_info.get("username"):
            user_folder = sanitize_username(sender_info["username"])
        elif sender_info.get("id"):
            user_folder = f"user_{sender_info['id']}"
        else:
            user_folder = "unknown_user"
        sender_display = format_user_info(sender_info)

    # Crea percorso per il salvataggio
    sanitized_group_name = sanitize_group_name(group_name)
    
    # Struttura: Downloads/[utente]/[gruppo]/[tipo_media]/
    group_dir = os.path.join(base_dir, app_nickname, sanitized_group_name, media_type)
    os.makedirs(group_dir, exist_ok=True)

    # Genera un nome file unico basato sul timestamp e ID del messaggio
    timestamp = int(message.date.timestamp() if hasattr(message, 'date') else time.time())
    file_name = f"{timestamp}_{message.id}"
    file_path = os.path.join(group_dir, file_name)

    # Scarica il media
    downloaded = await safe_download_media(message, file_path)
    
    if downloaded:
        # Registra info sul media in un file JSON di metadati
        metadata_file = os.path.join(os.path.dirname(os.path.dirname(group_dir)), "media_metadata.txt")
        with open(metadata_file, "a", encoding="utf-8") as f:
            date_str = message.date.strftime('%Y-%m-%d %H:%M:%S') if hasattr(message, 'date') else time.strftime('%Y-%m-%d %H:%M:%S')
            media_size = os.path.getsize(downloaded) if os.path.exists(downloaded) else "unknown"
            f.write(f"[{date_str}] File: {os.path.basename(downloaded)} | Gruppo: {group_name} | " +
                    f"Tipo: {media_type} | Da: {sender_display} | Dimensione: {media_size} bytes\n")
    
    return downloaded

async def save_message_content(group_name, message, app_nickname=None, base_dir=DOWNLOADS_DIR, sender_info=None):
    """Salva il contenuto testuale di un messaggio."""
    # Prepara informazioni sull'utente
    if not sender_info:
        user_id = message.sender_id if hasattr(message, 'sender_id') else "unknown"
        sender_display = f"User_{user_id}"
    else:
        sender_display = format_user_info(sender_info)

    sanitized_group_name = sanitize_group_name(group_name)
    
    # Struttura: Downloads/[utente]/[gruppo]/
    user_group_dir = os.path.join(base_dir, app_nickname, sanitized_group_name)
    os.makedirs(user_group_dir, exist_ok=True)

    # File per i messaggi di testo per questo gruppo e utente
    file_path = os.path.join(user_group_dir, "messages.txt")
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            text = message.text or message.message or "<vuoto>"
            date_str = message.date.strftime('%Y-%m-%d %H:%M:%S') if hasattr(message, 'date') else "unknown_date"
            f.write(f"[{date_str}] {sender_display}: {text}\n")
        
        if VERBOSE:
            print(f"💬 Salvato messaggio da {sender_display}")
        return True
    except Exception as e:
        log_error(f"Errore salvataggio messaggio: {e}\n{traceback.format_exc()}")
        return False

async def download_temporary_media(message, client, sender_id, app_nickname=None, sender_info=None):
    """Scarica temporaneamente un media per l'inoltro."""
    if sender_info and sender_info.get("username"):
        sender_name = sanitize_username(sender_info["username"])
    else:
        try:
            sender = await client.get_entity(sender_id)
            sender_name = sender.username or f"user_{sender_id}"
            sender_name = sanitize_username(sender_name)
        except Exception:
            sender_name = f"user_{sender_id}"
    
    # Personalizza la cartella temporanea per questo utente
    if app_nickname:
        sender_folder = os.path.join(TEMP_DIR, app_nickname, sender_name)
    else:
        sender_folder = os.path.join(TEMP_DIR, sender_name)
        
    os.makedirs(sender_folder, exist_ok=True)

    media_type = get_media_type(message)
    if media_type == "others":
        return None

    timestamp = int(time.time())
    file_name = f"{timestamp}_{message.id}"
    file_path = os.path.join(sender_folder, file_name)

    return await safe_download_media(message, file_path)

async def forward_media_clear(client, recipient_id, file_path, sender_id=None, sender_info=None):
    """Inoltra un media in chiaro a un destinatario."""
    if not os.path.exists(file_path):
        return False

    try:
        # Prepara la didascalia con informazioni dettagliate sul mittente
        if sender_info:
            sender_display = format_user_info(sender_info)
            caption = f"Media inviato da {sender_display}"
        elif sender_id:
            try:
                sender = await client.get_entity(sender_id)
                sender_username = f"@{sender.username}" if getattr(sender, 'username', None) else None
                sender_name = utils.get_display_name(sender)
                caption = f"Media inviato da {sender_name}"
                if sender_username:
                    caption += f" ({sender_username})"
            except Exception:
                caption = f"Media inviato da User_{sender_id}"
        else:
            caption = "Media inviato"

        # Determina se inviare come documento o media
        mime_type, _ = mimetypes.guess_type(file_path)
        is_media = mime_type and mime_type.startswith(("image/", "video/"))

        await client.send_file(
            recipient_id,
            file_path,
            caption=caption,
            force_document=not is_media
        )

        print(f"✅ Media inoltrato a {recipient_id}")
        return True
    except Exception as e:
        log_error(f"Errore forwarding media: {e}\n{traceback.format_exc()}")
        return False

def log_saved_media(sender_id, recipient_id, file_path, app_nickname=None, sender_info=None, recipient_info=None):
    """Registra l'operazione di inoltro media."""
    if app_nickname:
        # Personalizza la cartella di log per questo utente
        log_dir = os.path.join(TEMP_DIR, app_nickname)
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "media_log.txt")
    else:
        os.makedirs(TEMP_DIR, exist_ok=True)
        log_file = os.path.join(TEMP_DIR, "media_log.txt")
    
    sender_display = format_user_info(sender_info) if sender_info else f"User_{sender_id}"
    recipient_display = format_user_info(recipient_info) if recipient_info else f"User_{recipient_id}"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | Da: {sender_display} | A: {recipient_display} | File: {file_path}\n")

async def create_client_for_operation(nickname, operation_id=None):
    """Crea un client Telegram per un'operazione specifica."""
    if operation_id:
        # Usa il session manager per creare o ottenere una sessione dedicata
        _, session_path = session_manager.create_session(nickname, "op")
    else:
        # Se non c'è operation_id, usa la sessione standard
        session_path = f'session_{nickname}'
    
    # Crea il client con la sessione
    client = TelegramClient(
        session_path,
        API_ID, 
        API_HASH,
        connection_retries=10,
        retry_delay=3
    )
    
    return client, session_path

async def download_group_archive(selected_group, instance_id=None, operation_id=None):
    """Scarica tutti i media disponibili di un gruppo selezionato."""
    if not selected_group:
        print("❌ Nessun gruppo selezionato.")
        return False
    
    nickname = selected_group["user"]
    group = selected_group["group"]
    group_id = group["id"]
    group_name = group["name"]
    
    print(f"\n📥 Avvio download archivio completo per: {group_name}")
    print(f"👤 Utente: {nickname}")
    print(f"🆔 ID Gruppo: {group_id}")
    
    # Crea directory per l'archivio, organizzata per utente dell'applicazione
    sanitized_group_name = sanitize_group_name(group_name)
    archive_path = os.path.join(ARCHIVE_DIR, nickname, sanitized_group_name)
    os.makedirs(archive_path, exist_ok=True)
    
    # File di log per questo specifico archivio
    log_file = os.path.join(archive_path, "download_log.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Avvio download archivio per {group_name} (ID: {group_id})\n")
    
    # Se non è stato fornito un operation_id, ne creiamo uno nuovo
    if not operation_id:
        operation_id = f"archive_{int(time.time())}_{random.randint(1000, 9999)}"
    
    client = None
    
    try:
        # Crea un client con una sessione dedicata per questa operazione
        client, session_path = await create_client_for_operation(nickname, operation_id)
        
        # Stampa l'ID del client per debug
        client_id = id(client)
        print(f"Debug: Client ID per download_group_archive: {client_id}")
        
        # Evita conflitti con altre istanze
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        # Tenta la connessione con retry
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                await client.start()
                print("✅ Client connesso per download archivio")
                break
            except Exception as e:
                if "database is locked" in str(e).lower() and attempt < max_attempts - 1:
                    print(f"⚠️ Database bloccato, nuovo tentativo in corso... ({attempt+1}/{max_attempts})")
                    await asyncio.sleep(random.uniform(1, 3) * (attempt + 1))
                else:
                    raise
        
        # Ottieni l'entità del gruppo
        try:
            target_group = await client.get_entity(group_id)
            print(f"✅ Gruppo trovato: {utils.get_display_name(target_group)}")
        except Exception as e:
            log_error(f"Impossibile trovare il gruppo: {e}")
            if client and client.is_connected():
                await client.disconnect()
                print(f"🔌 Client disconnesso (ID: {client_id})")
            return False
        
        # Statistiche
        total_messages = 0
        media_count = 0
        text_count = 0
        users_found = set()
        
        # Timestamp per monitoraggio
        start_time = time.time()
        last_update = start_time
        
        print("\n⏳ Download in corso... (potrebbe richiedere tempo)")
        
        # Cache degli utenti per evitare richieste ripetute
        user_cache = {}
        
        # Scarica tutti i messaggi
        async for message in client.iter_messages(target_group):
            total_messages += 1
            
            # Aggiorna lo stato ogni 50 messaggi o ogni 10 secondi
            current_time = time.time()
            if total_messages % 50 == 0 or current_time - last_update > 10:
                print(f"💬 Messaggi processati: {total_messages} (Media: {media_count}, Testo: {text_count}, Utenti: {len(users_found)})")
                last_update = current_time
            
            # Ottieni informazioni sul mittente
            sender_id = message.sender_id
            if sender_id:
                if sender_id not in user_cache:
                    try:
                        sender = await client.get_entity(sender_id)
                        user_cache[sender_id] = {
                            "id": sender_id,
                            "username": getattr(sender, 'username', None),
                            "first_name": getattr(sender, 'first_name', None),
                            "last_name": getattr(sender, 'last_name', None),
                            "display_name": utils.get_display_name(sender)
                        }
                        users_found.add(sender_id)
                    except Exception:
                        user_cache[sender_id] = {"id": sender_id, "display_name": f"User_{sender_id}"}
                
                sender_info = user_cache[sender_id]
                sender_display = format_user_info(sender_info)
            else:
                sender_info = None
                sender_display = "Mittente sconosciuto"
            
            # Salva il testo del messaggio
            if message.text or message.message:
                await save_message_content(group_name, message, nickname, ARCHIVE_DIR, sender_info=sender_info)
                text_count += 1
                if VERBOSE:
                    print(f"💬 Salvato messaggio di {sender_display}")
            
            # Scarica il media se presente
            if message.media:
                media_type = get_media_type(message)
                if media_type != "others":
                    result = await download_media(message, group_name, nickname, ARCHIVE_DIR, sender_info=sender_info)
                    if result:
                        media_count += 1
                        if VERBOSE:
                            print(f"📥 Salvato {media_type} di {sender_display}")
        
        # Salva informazioni sugli utenti
        users_file = os.path.join(archive_path, "users.txt")
        with open(users_file, "w", encoding="utf-8") as f:
            f.write(f"Utenti nel gruppo {group_name} ({group_id}):\n")
            f.write("=" * 50 + "\n")
            for user_id in sorted(user_cache.keys()):
                user = user_cache[user_id]
                user_display = format_user_info(user)
                f.write(f"- {user_display}\n")
        
        # Statistiche finali
        duration = time.time() - start_time
        print(f"\n✅ Download completato in {duration:.1f} secondi")
        print(f"📊 Statistiche:")
        print(f"   - Messaggi totali: {total_messages}")
        print(f"   - Media scaricati: {media_count}")
        print(f"   - Messaggi di testo: {text_count}")
        print(f"   - Utenti trovati: {len(users_found)}")
        print(f"📁 Archivio salvato in: {os.path.abspath(archive_path)}")
        print(f"👥 Elenco degli utenti salvato in: {os.path.abspath(users_file)}")
        
        # Aggiorna il log
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Download completato\n")
            f.write(f"Messaggi totali: {total_messages}\n")
            f.write(f"Media scaricati: {media_count}\n")
            f.write(f"Messaggi di testo: {text_count}\n")
            f.write(f"Utenti trovati: {len(users_found)}\n")
            f.write(f"Durata: {duration:.1f} secondi\n")
        
        return True
    except Exception as e:
        log_error(f"Errore durante il download dell'archivio: {e}\n{traceback.format_exc()}")
        return False
    finally:
        # Disconnetti il client SOLO se è ancora definito e connesso
        # Utilizziamo una variabile locale per evitare conflitti con altri client
        try:
            if client and client.is_connected():
                client_id = id(client)
                await client.disconnect()
                print(f"🔌 Client disconnesso per download archivio (ID: {client_id})")
        except Exception as e:
            log_error(f"Errore durante la disconnessione del client: {e}")
            
        # Rilascia la sessione
        if operation_id:
            session_manager.release_session(operation_id, nickname)