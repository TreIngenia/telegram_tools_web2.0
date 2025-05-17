import asyncio
import os
import random
import time
from telethon import TelegramClient, events, utils

# Importa il session manager
from gui_session_manager import session_manager

from config import API_ID, API_HASH, PHONE_NUMBERS_FILE
from utils import load_json, log_error, format_user_info
from media_handler import (
    download_media, save_message_content, 
    download_temporary_media, forward_media_clear, 
    log_saved_media
)

# Dizionario per tenere traccia dei client attivi
active_clients = {}

async def get_user_info(client, user_id):
    """Ottiene informazioni dettagliate su un utente."""
    try:
        user = await client.get_entity(user_id)
        username = user.username if getattr(user, 'username', None) else None
        first_name = getattr(user, 'first_name', None)
        last_name = getattr(user, 'last_name', None)
        
        # Costruisci un dizionario con le informazioni disponibili
        user_info = {
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "display_name": utils.get_display_name(user)
        }
        return user_info
    except Exception as e:
        log_error(f"Impossibile ottenere informazioni sull'utente {user_id}: {e}")
        return {"id": user_id, "display_name": f"User_{user_id}"}

async def handle_event(client, bot_entity, event, nickname):
    """Gestisce gli eventi dei messaggi in arrivo."""
    sender_id = event.sender_id
    chat_id = event.chat_id
    
    # Ignora i messaggi inviati dal bot stesso
    if sender_id == bot_entity.id:
        return

    try:
        # Ottieni informazioni sul mittente
        sender_info = await get_user_info(client, sender_id)
        user_display = format_user_info(sender_info)
        
        # Messaggi da gruppi o canali
        if event.is_group or event.is_channel:
            # Ottieni il nome del gruppo
            try:
                chat_entity = await client.get_entity(chat_id)
                group_name = chat_entity.title
                group_display = f"{group_name} ({chat_id})"
            except Exception as e:
                log_error(f"Impossibile ottenere il nome del gruppo: {e}")
                group_name = str(chat_id)
                group_display = f"Gruppo {chat_id}"

            if event.message.media:
                print(f"📥 Ricevuto media in {group_display} da {user_display}")
                media_path = await download_media(event.message, group_name, nickname, sender_info=sender_info)
                if media_path:
                    print(f"✅ Media salvato: {media_path}")
            
            # Salva il contenuto del messaggio se presente
            if event.message.text or event.message.message:
                print(f"💬 Messaggio in {group_display} da {user_display}")
                await save_message_content(group_name, event.message, nickname, sender_info=sender_info)

        # Messaggi privati con media
        elif event.is_private and event.message.media:
            print(f"📩 Ricevuto media temporaneo da {user_display}")

            # Ottieni l'entità della chat
            try:
                chat_entity = await client.get_entity(chat_id)
            except Exception as e:
                log_error(f"Impossibile ottenere l'entità della chat: {e}")
                return

            # Determina il destinatario effettivo
            actual_recipient_id = None
            if hasattr(chat_entity, 'participants'):
                participants = chat_entity.participants
                for participant in participants:
                    if participant.id != sender_id:
                        actual_recipient_id = participant.id
                        break
            else:
                actual_recipient_id = bot_entity.id

            # Scarica temporaneamente il media
            temp_media_path = await download_temporary_media(event.message, client, sender_id, nickname, sender_info=sender_info)

            # Inoltra il media in chiaro se è stato scaricato e c'è un destinatario
            if temp_media_path and actual_recipient_id:
                if actual_recipient_id != sender_id:
                    recipient_info = await get_user_info(client, actual_recipient_id)
                    recipient_display = format_user_info(recipient_info)
                    print(f"📤 Inoltro media in chiaro da {user_display} a {recipient_display}")
                    await forward_media_clear(client, actual_recipient_id, temp_media_path, sender_id, sender_info=sender_info)
                    log_saved_media(sender_id, actual_recipient_id, temp_media_path, nickname, sender_info=sender_info, recipient_info=recipient_info)
                else:
                    print(f"⚠️ Il destinatario è il mittente stesso, non inoltro il media")
    except Exception as e:
        log_error(f"Errore durante la gestione dell'evento: {e}")

async def start_monitoring(instance_id=None):
    """Avvia il monitoraggio per tutti gli utenti configurati."""
    global active_clients
    
    # Crea un operation_id per questo monitoraggio
    operation_id = f"monitor_{instance_id or int(time.time())}"
    
    phone_numbers = load_json(PHONE_NUMBERS_FILE)
    tasks = []

    if not phone_numbers:
        print("❌ Nessun utente configurato. Aggiungi almeno un utente.")
        return False

    for nickname, phone_number in phone_numbers.items():
        # Crea una sessione dedicata per questo monitoraggio
        _, session_path = session_manager.create_session(nickname, operation_id)
        
        # Utilizza un client univoco per ogni istanza+nickname
        client_key = f"{operation_id}_{nickname}"
        
        # Chiudi eventuali client esistenti con la stessa chiave
        if client_key in active_clients:
            try:
                old_client = active_clients[client_key]
                if old_client.is_connected():
                    await old_client.disconnect()
                del active_clients[client_key]
            except:
                pass
        
        # Crea un nuovo client con la sessione dedicata
        client = TelegramClient(
            session_path,
            API_ID, 
            API_HASH,
            connection_retries=10,
            retry_delay=3
        )
        
        # Stampa l'ID del client per debug
        client_id = id(client)
        print(f"Debug: Client ID per monitoraggio {nickname}: {client_id}")
        
        active_clients[client_key] = client

        async def run_client(nickname, phone_number, client, client_key):
            try:
                # Attendi un po' per evitare conflitti tra istanze
                await asyncio.sleep(random.uniform(0.3, 1.0))
                
                async with client:
                    client_id = id(client)
                    # Aggiungi tentativi multipli per il login
                    max_attempts = 5
                    for attempt in range(max_attempts):
                        try:
                            await client.start(phone_number)
                            break
                        except Exception as e:
                            if "database is locked" in str(e).lower() and attempt < max_attempts - 1:
                                print(f"⚠️ Database bloccato, nuovo tentativo in corso... ({attempt+1}/{max_attempts})")
                                await asyncio.sleep(random.uniform(1, 3) * (attempt + 1))
                            else:
                                raise
                    
                    bot_entity = await client.get_me()
                    bot_info = await get_user_info(client, bot_entity.id)
                    bot_display = format_user_info(bot_info)
                    
                    # Registra l'handler per i nuovi messaggi, passando il nickname
                    @client.on(events.NewMessage(incoming=True, outgoing=False))
                    async def handler(event):
                        await handle_event(client, bot_entity, event, nickname)

                    print(f"🔄 Monitoraggio attivo per {bot_display} (Nickname: {nickname}) [Istanza: {instance_id or 'principale'}] [Client ID: {client_id}]")
                    
                    # Rimani in ascolto finché il client non si disconnette
                    await client.run_until_disconnected()
            except Exception as e:
                log_error(f"Errore nel client {nickname} (ID: {id(client)}): {e}")
            finally:
                # Rimuovi il client dalla lista dei client attivi
                if client_key in active_clients:
                    c_id = id(active_clients[client_key])
                    print(f"Rimozione client {nickname} dal monitoraggio (ID: {c_id})")
                    del active_clients[client_key]
                
        tasks.append(run_client(nickname, phone_number, client, client_key))

    try:
        await asyncio.gather(*tasks)
        return True
    except KeyboardInterrupt:
        # Chiudi tutte le connessioni prima di uscire
        for client_key, client in list(active_clients.items()):
            try:
                if client.is_connected():
                    client_id = id(client)
                    await client.disconnect()
                    print(f"🔌 Client monitoraggio disconnesso durante KeyboardInterrupt (ID: {client_id})")
            except:
                pass
        active_clients.clear()
        raise
    finally:
        # Rilascia tutte le sessioni per questa operazione
        print(f"Rilascio sessioni per operazione di monitoraggio: {operation_id}")
        session_manager.release_session(operation_id)

def cleanup_session_files(instance_id):
    """Pulisce i file di sessione temporanei per questa istanza."""
    # Usa il session manager per pulire le sessioni
    session_manager.cleanup_all()
    
    # Per retrocompatibilità, pulisci anche i file con il vecchio formato
    try:
        # Trova tutti i file di sessione per questa istanza
        for file in os.listdir('.'):
            if file.endswith('.session') and f'_{instance_id}' in file:
                try:
                    os.remove(file)
                except:
                    pass
                    
                # Rimuovi anche eventuali file correlati
                base_name = file.replace('.session', '')
                for ext in ['.session-journal', '-journal']:
                    related_file = f'{base_name}{ext}'
                    if os.path.exists(related_file):
                        try:
                            os.remove(related_file)
                        except:
                            pass
    except Exception as e:
        log_error(f"Errore durante la pulizia dei file di sessione: {e}")