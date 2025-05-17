import os
import json
import time
import re
import emoji
import traceback
import asyncio
import sys
import platform
import subprocess
from config import DOWNLOADS_DIR

def log_error(message):
    """Registra un errore in un file di log."""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    with open(os.path.join(DOWNLOADS_DIR, "errors.txt"), "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    print(f"❌ ERRORE: {message}")

def log_info(message, file_name="info.txt"):
    """Registra un'informazione in un file di log."""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    with open(os.path.join(DOWNLOADS_DIR, file_name), "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

def load_json(file_path):
    """Carica dati da un file JSON."""
    try:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    # Se il file è vuoto, restituisci un dizionario vuoto
                    if not content:
                        return {}
                    return json.loads(content)
            except json.JSONDecodeError as e:
                log_error(f"Errore nel decodificare il file JSON {file_path}: {e}")
                # Backup del file corrotto
                backup_file = f"{file_path}.backup_{int(time.time())}"
                try:
                    if os.path.exists(file_path):
                        os.rename(file_path, backup_file)
                        log_error(f"File JSON corrotto. Backup creato: {backup_file}")
                except Exception as e:
                    log_error(f"Impossibile creare backup del file JSON corrotto: {e}")
    except Exception as e:
        log_error(f"Errore generico nel caricamento del file JSON {file_path}: {e}")
    
    return {}

def save_json(file_path, data):
    """Salva dati in un file JSON."""
    try:
        # Crea la directory se non esiste
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # Utilizza un file temporaneo per evitare corruzione in caso di crash
        temp_file = f"{file_path}.temp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        # Rinomina il file temporaneo nel file finale (operazione atomica)
        if os.path.exists(file_path):
            os.replace(temp_file, file_path)
        else:
            os.rename(temp_file, file_path)
        
        return True
    except Exception as e:
        log_error(f"Errore nel salvare il file JSON {file_path}: {e}")
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        return False

def sanitize_group_name(name):
    """Sanitizza il nome di un gruppo per usarlo come nome di directory."""
    if isinstance(name, int) or (isinstance(name, str) and name.strip('-').isdigit()):
        return f"group_{name}"  # Converti gli ID numerici in un formato di nome

    name = emoji.demojize(name)
    name = re.sub(r'[^a-zA-Z0-9\s:]', '', name)
    name = name.replace(":", "_").replace(" ", "_")
    return name

def sanitize_username(username):
    """Sanitizza un username per usarlo come nome di directory."""
    if not username:
        return "unknown_user"
        
    # Rimuovi @ se presente
    if username.startswith('@'):
        username = username[1:]
        
    # Converti in formato valido per directory
    username = re.sub(r'[^a-zA-Z0-9_]', '', username)
    
    # Se vuoto dopo la sanitizzazione
    if not username:
        return "unknown_user"
        
    return username

def format_user_info(user_info):
    """Formatta le informazioni dell'utente per la visualizzazione."""
    if not user_info:
        return "Utente sconosciuto"
        
    # Costruisci la stringa di visualizzazione con informazioni disponibili
    parts = []
    
    # Aggiungi il nome visualizzato se disponibile
    if user_info.get("display_name"):
        parts.append(user_info["display_name"])
    elif user_info.get("first_name"):
        name_parts = [user_info["first_name"]]
        if user_info.get("last_name"):
            name_parts.append(user_info["last_name"])
        parts.append(" ".join(name_parts))
        
    # Aggiungi username se disponibile
    if user_info.get("username"):
        parts.append(f"@{user_info['username']}")
    
    # Aggiungi sempre l'ID per riferimento
    parts.append(f"(ID: {user_info['id']})")
    
    return " ".join(parts)

async def retry_operation(func, *args, retries=3, delay=1, **kwargs):
    """Esegue un'operazione con tentativi multipli in caso di fallimento."""
    for attempt in range(1, retries + 2):
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            if attempt <= retries:
                print(f"⚠️ Tentativo {attempt}/{retries} fallito: {e}")
                await asyncio.sleep(delay)
            else:
                log_error(f"Operazione fallita dopo {retries} tentativi: {e}\n{traceback.format_exc()}")
                raise
    return None

def get_instance_id():
    """Genera un ID univoco per l'istanza corrente del programma."""
    return f"{int(time.time())}-{os.getpid()}"

def acquire_lock(lock_file, instance_id):
    """Acquisisci un lock esclusivo per operazioni di modifica del file di istanze."""
    lock_acquired = False
    max_retries = 5
    retry_delay = 0.2  # 200ms
    
    lock_path = f"{lock_file}.lock"
    
    for attempt in range(max_retries):
        try:
            if not os.path.exists(lock_path):
                # Crea file di lock con ID dell'istanza
                with open(lock_path, "w", encoding="utf-8") as f:
                    f.write(f"{instance_id}")
                lock_acquired = True
                break
            else:
                # Verifica se il lock è scaduto (più di 5 secondi)
                try:
                    mtime = os.path.getmtime(lock_path)
                    if time.time() - mtime > 5:
                        # Lock scaduto, sovrascrivilo
                        with open(lock_path, "w", encoding="utf-8") as f:
                            f.write(f"{instance_id}")
                        lock_acquired = True
                        break
                except:
                    pass
            
            # Attendi prima del prossimo tentativo
            time.sleep(retry_delay)
        except Exception as e:
            log_error(f"Errore durante l'acquisizione del lock: {e}")
            time.sleep(retry_delay)
    
    return lock_acquired

def release_lock(lock_file, instance_id):
    """Rilascia il lock se posseduto da questa istanza."""
    lock_path = f"{lock_file}.lock"
    
    try:
        if os.path.exists(lock_path):
            # Verifica che il lock sia di questa istanza
            try:
                with open(lock_path, "r", encoding="utf-8") as f:
                    lock_owner = f.read().strip()
                
                if lock_owner == instance_id:
                    os.remove(lock_path)
                    return True
            except:
                # Se c'è un errore, prova comunque a rimuovere il lock
                try:
                    os.remove(lock_path)
                except:
                    pass
    except Exception as e:
        log_error(f"Errore durante il rilascio del lock: {e}")
    
    return False

def register_instance(instance_id, lock_file):
    """Registra un'istanza in esecuzione."""
    if not acquire_lock(lock_file, instance_id):
        log_error(f"Impossibile acquisire il lock per la registrazione dell'istanza {instance_id}")
        return False
    
    try:
        instances = load_json(lock_file)
        instances[instance_id] = {
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pid": os.getpid()
        }
        result = save_json(lock_file, instances)
        return result
    except Exception as e:
        log_error(f"Errore durante la registrazione dell'istanza: {e}")
        return False
    finally:
        release_lock(lock_file, instance_id)

def unregister_instance(instance_id, lock_file):
    """Rimuove un'istanza dal registro."""
    if not acquire_lock(lock_file, instance_id):
        log_error(f"Impossibile acquisire il lock per la rimozione dell'istanza {instance_id}")
        return False
    
    try:
        instances = load_json(lock_file)
        if instance_id in instances:
            del instances[instance_id]
            result = save_json(lock_file, instances)
            return result
        return False
    except Exception as e:
        log_error(f"Errore durante la rimozione dell'istanza: {e}")
        return False
    finally:
        release_lock(lock_file, instance_id)

def is_process_running(pid):
    """Verifica se un processo con il PID specificato è in esecuzione in modo cross-platform."""
    if pid is None:
        return False
    
    try:
        # Rileva il sistema operativo
        current_os = platform.system().lower()
        
        if current_os == 'windows':
            # Metodo Windows usando tasklist
            try:
                # Usa tasklist per elencare i processi con il PID specificato
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}', '/NH'], 
                    capture_output=True, 
                    text=True, 
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                # Se il pid è presente nell'output di tasklist
                return str(pid) in result.stdout
            except Exception as e:
                # Fallback: se subprocess fallisce, usa psutil se disponibile
                try:
                    import psutil
                    return psutil.pid_exists(pid)
                except ImportError:
                    # Se psutil non è disponibile, supponiamo che il processo sia attivo
                    # per evitare terminazioni improprie
                    return True
        else:  # Linux, macOS, ecc.
            # Su Unix, proviamo il metodo standard con os.kill
            os.kill(pid, 0)  # Il segnale 0 non fa nulla, verifica solo l'esistenza
            return True
    except OSError:
        # OSError significa che il processo non esiste
        return False
    except Exception as e:
        # Log dell'errore ma restituisci False per sicurezza
        log_error(f"Errore nella verifica del processo {pid}: {e}")
        return False

def check_running_instances(lock_file):
    """Controlla e pulisce le istanze registrate."""
    if not os.path.exists(lock_file):
        return {}
    
    if not acquire_lock(lock_file, "checker"):
        print("⚠️ Impossibile acquisire il lock per verificare le istanze. Riprova tra poco.")
        return load_json(lock_file)  # Restituisci le istanze senza modifiche
    
    try:
        instances = load_json(lock_file)
        active_instances = {}
        removed_instances = []
        
        for instance_id, info in instances.items():
            pid = info.get("pid")
            # Verifica se il processo è ancora attivo
            if pid and is_process_running(pid):
                active_instances[instance_id] = info
            else:
                removed_instances.append(instance_id)
        
        # Mostra quali istanze sono state rimosse
        for instance_id in removed_instances:
            print(f"🧹 Rimossa istanza non attiva: {instance_id}")
        
        # Aggiorna il file con solo le istanze attive
        if active_instances != instances:
            save_json(lock_file, active_instances)
        
        return active_instances
    except Exception as e:
        log_error(f"Errore durante la verifica delle istanze: {e}")
        return {}  # In caso di errore, restituisci un dizionario vuoto per sicurezza
    finally:
        release_lock(lock_file, "checker")