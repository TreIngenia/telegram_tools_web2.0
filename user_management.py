import os
import time
import random
import asyncio
from telethon import TelegramClient
from utils import load_json, save_json, log_error
from config import API_ID, API_HASH, PHONE_NUMBERS_FILE

async def create_client(nickname):
    """Crea un client con gestione migliorata delle sessioni."""
    # Usa il client standard ma con parametri migliorati
    session_path = f'session_{nickname}'
    client = TelegramClient(
        session_path, 
        API_ID, 
        API_HASH,
        connection_retries=10,
        retry_delay=3
    )
    return client

def add_new_user():
    """Aggiunge un nuovo utente al sistema."""
    phone_numbers = load_json(PHONE_NUMBERS_FILE)
    
    nickname = input("Inserisci il nickname dell'utente: ").strip()
    if not nickname:
        print("❌ Il nickname non può essere vuoto.")
        return False
        
    if nickname in phone_numbers:
        print(f"⚠️ Il nickname '{nickname}' esiste già.")
        replace = input("Vuoi sovrascriverlo? (s/n): ").strip().lower()
        if replace != 's':
            return False
    
    phone_number = input(f"Inserisci il numero di telefono per {nickname}: ").strip()
    if not phone_number:
        print("❌ Il numero di telefono non può essere vuoto.")
        return False
    
    # Usa asyncio.run per eseguire la verifica asincrona
    try:
        return asyncio.run(verify_and_add_user(nickname, phone_number))
    except Exception as e:
        log_error(f"Errore durante l'aggiunta dell'utente: {e}")
        print(f"❌ Errore: {e}")
        return False

async def verify_and_add_user(nickname, phone_number):
    """Verifica e aggiunge un utente in modo asincrono."""
    # Crea il client con gestione migliorata
    client = await create_client(nickname)
    
    try:
        # Evita conflitti con altre istanze
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        # Aggiungi tentativi multipli per l'avvio
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
        
        # Se arriviamo qui, la connessione è riuscita
        await client.disconnect()
        
        # Aggiorna il file degli utenti
        phone_numbers = load_json(PHONE_NUMBERS_FILE)
        phone_numbers[nickname] = phone_number
        save_json(PHONE_NUMBERS_FILE, phone_numbers)
        print(f"✅ Utente {nickname} aggiunto con successo!")
        return True
    except Exception as e:
        if client.is_connected():
            await client.disconnect()
        log_error(f"Errore durante la verifica dell'account: {e}")
        print(f"❌ Errore durante la verifica dell'account: {e}")
        return False

def remove_user():
    """Rimuove un utente dal sistema."""
    phone_numbers = load_json(PHONE_NUMBERS_FILE)
    
    if not phone_numbers:
        print("❌ Nessun utente salvato.")
        return False
        
    show_saved_users()
    nickname = input("\nInserisci il nickname dell'utente da rimuovere: ").strip()
    
    if nickname not in phone_numbers:
        print(f"❌ Utente '{nickname}' non trovato.")
        return False
        
    confirm = input(f"Sei sicuro di voler rimuovere l'utente '{nickname}'? (s/n): ").strip().lower()
    if confirm != 's':
        print("Operazione annullata.")
        return False
        
    # Rimuove l'utente dal file
    del phone_numbers[nickname]
    save_json(PHONE_NUMBERS_FILE, phone_numbers)
    
    # Rimuove il file di sessione se esiste
    session_file = f'session_{nickname}.session'
    if os.path.exists(session_file):
        try:
            # Attendi un po' per assicurarsi che il file non sia in uso
            time.sleep(0.5)
            os.remove(session_file)
        except Exception as e:
            print(f"⚠️ Impossibile rimuovere il file di sessione: {e}")
    
    print(f"✅ Utente '{nickname}' rimosso con successo.")
    return True

def show_saved_users():
    """Mostra tutti gli utenti salvati."""
    phone_numbers = load_json(PHONE_NUMBERS_FILE)
    
    if not phone_numbers:
        print("Nessun utente salvato.")
        return False
        
    print("\n📋 Utenti salvati:")
    for i, (nickname, phone) in enumerate(phone_numbers.items(), 1):
        print(f"{i}. {nickname}: {phone}")
    return True

async def check_user_auth(nickname, phone_number):
    """Verifica se l'utente è autenticato correttamente."""
    # Crea il client con gestione migliorata
    client = await create_client(nickname)
    
    try:
        # Evita conflitti con altre istanze
        await asyncio.sleep(random.uniform(0.2, 0.5))
        
        # Aggiungi tentativi multipli per l'avvio
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
                    
        # Ottieni info utente
        me = await client.get_me()
        await client.disconnect()
        return True, me.username or f"ID: {me.id}"
    except Exception as e:
        if client.is_connected():
            await client.disconnect()
        return False, str(e)