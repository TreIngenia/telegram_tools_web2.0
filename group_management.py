import asyncio
import os
import random
import shutil
from telethon import TelegramClient, errors
from utils import load_json, save_json, sanitize_group_name, log_error
from config import API_ID, API_HASH, USER_GROUPS_FILE, PHONE_NUMBERS_FILE

async def create_client_for_instance(nickname, instance_id=None):
    """Crea un client con sessione dedicata per questa istanza."""
    # Sessione originale
    original_session = f'session_{nickname}.session'
    
    if instance_id:
        # Crea una sessione dedicata per questa istanza
        instance_session = f'session_{nickname}_{instance_id}.session'
        
        # Copia il file di sessione originale per creare una sessione dedicata
        if os.path.exists(original_session) and not os.path.exists(instance_session):
            try:
                shutil.copy2(original_session, instance_session)
            except Exception as e:
                log_error(f"Errore nella copia del file di sessione: {e}")
                # Se non riusciamo a copiare, continuiamo comunque con il file originale
                instance_session = original_session
        elif not os.path.exists(original_session):
            # Se il file originale non esiste, usalo comunque (verrà creato)
            instance_session = original_session
            
        # Crea il client con la sessione dell'istanza
        client = TelegramClient(
            instance_session.replace('.session', ''),  # Rimuovi l'estensione
            API_ID, 
            API_HASH,
            connection_retries=10,
            retry_delay=3
        )
    else:
        # Se non c'è ID istanza, usa la sessione originale
        client = TelegramClient(
            original_session.replace('.session', ''),
            API_ID, 
            API_HASH,
            connection_retries=10,
            retry_delay=3
        )
    
    return client

async def list_chats(client, nickname):
    """Elenca tutti i gruppi e canali disponibili per un utente."""
    groups = []
    try:
        print(f"\nRecupero gruppi per {nickname}...")
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                username = f"@{dialog.entity.username}" if getattr(dialog.entity, 'username', None) else f"ID: {dialog.id}"
                ascii_name = sanitize_group_name(dialog.name)
                groups.append({
                    "name": dialog.name,
                    "ascii_name": ascii_name,
                    "id": dialog.id,
                    "link": username,
                    "members_count": getattr(dialog.entity, 'participants_count', 0)
                })
                print(f"- {dialog.name} ({username}) - Membri: {getattr(dialog.entity, 'participants_count', 'N/A')}")
        return groups
    except Exception as e:
        log_error(f"Errore durante il recupero dei gruppi per {nickname}: {e}")
        return []

async def get_all_user_groups(instance_id=None):
    """Recupera tutti i gruppi per tutti gli utenti."""
    phone_numbers = load_json(PHONE_NUMBERS_FILE)
    user_groups = {}
    tasks = []
    temp_sessions = []

    if not phone_numbers:
        print("❌ Nessun utente salvato. Aggiungi almeno un utente.")
        return False

    for nickname, phone_number in phone_numbers.items():
        async def get_groups_for_user(nickname, phone_number):
            # Utilizza il client migliorato
            user_client = await create_client_for_instance(nickname, instance_id)
            if instance_id:
                temp_sessions.append(f'session_{nickname}_{instance_id}.session')
                
            try:
                # Evita conflitti con altre istanze
                await asyncio.sleep(random.uniform(0.2, 0.5))
                
                # Aggiungi tentativi multipli per l'avvio
                max_attempts = 5
                for attempt in range(max_attempts):
                    try:
                        await user_client.start(phone_number)
                        break
                    except Exception as e:
                        if "database is locked" in str(e).lower() and attempt < max_attempts - 1:
                            print(f"⚠️ Database bloccato, nuovo tentativo in corso... ({attempt+1}/{max_attempts})")
                            await asyncio.sleep(random.uniform(1, 3) * (attempt + 1))
                        else:
                            raise
                
                groups = await list_chats(user_client, nickname)
                await user_client.disconnect()
                return nickname, groups
            except Exception as e:
                log_error(f"Errore per l'utente {nickname}: {e}")
                if user_client.is_connected():
                    await user_client.disconnect()
                return nickname, []

        tasks.append(get_groups_for_user(nickname, phone_number))

    try:
        results = await asyncio.gather(*tasks)
        
        for nickname, groups in results:
            if groups:
                user_groups[nickname] = groups
        
        if not user_groups:
            print("❌ Nessun gruppo trovato per nessun utente.")
            return False
            
        save_json(USER_GROUPS_FILE, user_groups)
        print(f"✅ Gruppi salvati in {USER_GROUPS_FILE}")
        return True
    finally:
        # Pulizia delle sessioni temporanee
        for session_file in temp_sessions:
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                except:
                    pass

async def get_group_link(chat_id, instance_id=None):
    """Ottiene il link di un gruppo dato il chat_id."""
    phone_numbers = load_json(PHONE_NUMBERS_FILE)
    temp_sessions = []
    
    if not phone_numbers:
        print("❌ Nessun utente salvato. Aggiungi almeno un utente.")
        return None
    
    for nickname, phone_number in phone_numbers.items():
        # Utilizza il client migliorato
        client = await create_client_for_instance(nickname, instance_id)
        if instance_id:
            temp_sessions.append(f'session_{nickname}_{instance_id}.session')
            
        try:
            # Evita conflitti con altre istanze
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Aggiungi tentativi multipli per l'avvio
            max_attempts = 5
            connected = False
            
            for attempt in range(max_attempts):
                try:
                    await client.start(phone_number)
                    connected = True
                    break
                except Exception as e:
                    if "database is locked" in str(e).lower() and attempt < max_attempts - 1:
                        print(f"⚠️ Database bloccato, nuovo tentativo in corso... ({attempt+1}/{max_attempts})")
                        await asyncio.sleep(random.uniform(1, 3) * (attempt + 1))
                    else:
                        raise
            
            if connected:
                try:
                    group = await client.get_entity(int(chat_id))
                    if hasattr(group, 'username') and group.username:
                        link = f"https://t.me/{group.username}"
                        print(f"🔗 Link del gruppo trovato con {nickname}: {link}")
                        await client.disconnect()
                        return link
                    else:
                        print(f"⚠️ Il gruppo ({chat_id}) trovato da {nickname} non ha un link pubblico.")
                except Exception as e:
                    print(f"⚠️ Utente {nickname} non può accedere al gruppo: {e}")
                finally:
                    if client.is_connected():
                        await client.disconnect()
        except Exception as e:
            print(f"❌ Errore di connessione con l'utente {nickname}: {e}")
            if client.is_connected():
                await client.disconnect()
        finally:
            # Pulizia delle sessioni temporanee
            for session_file in temp_sessions:
                if os.path.exists(session_file):
                    try:
                        os.remove(session_file)
                    except:
                        pass
        
        print("❌ Nessun utente ha accesso a questo gruppo.")
        return None

def display_all_groups():
    """Mostra tutti i gruppi disponibili in formato numerato."""
    user_groups = load_json(USER_GROUPS_FILE)
    
    if not user_groups:
        print("❌ Nessun gruppo trovato. Esegui prima 'Mostra gruppi disponibili'.")
        return None
    
    all_groups = []
    
    print("\n📋 Gruppi disponibili:")
    group_index = 1
    
    for nickname, groups in user_groups.items():
        print(f"\n👤 Utente: {nickname}")
        
        if not groups:
            print("  Nessun gruppo disponibile per questo utente.")
            continue
            
        for group in groups:
            print(f"  {group_index}. {group['name']} ({group['link']}) - Membri: {group.get('members_count', 'N/A')}")
            all_groups.append({
                "index": group_index,
                "user": nickname,
                "group": group
            })
            group_index += 1
    
    return all_groups

def select_group_for_action():
    """Permette all'utente di selezionare un gruppo dalla lista numerata."""
    all_groups = display_all_groups()
    
    if not all_groups:
        return None
    
    try:
        choice = int(input("\nSeleziona il numero del gruppo: ").strip())
        
        for group_data in all_groups:
            if group_data["index"] == choice:
                selected = group_data
                print(f"\n✅ Hai selezionato: {selected['group']['name']} dell'utente {selected['user']}")
                return selected
        
        print(f"❌ Numero {choice} non valido. Riprova.")
        return None
    except ValueError:
        print("❌ Inserisci un numero valido.")
        return None