import os
import sys
import asyncio
import time
import random
from config import LOCK_FILE
from utils import get_instance_id, register_instance, unregister_instance, check_running_instances, log_error
from user_management import add_new_user, remove_user, show_saved_users
from group_management import get_all_user_groups, get_group_link, select_group_for_action
from media_handler import download_group_archive
from event_handler import start_monitoring, cleanup_session_files
from multiinstance import show_running_instances

async def archive_menu(instance_id):
    """Menu per la gestione degli archivi."""
    while True:
        print("\n==== Menu Archivio ====")
        print("1) Elenca tutti i gruppi")
        print("2) Scarica archivio completo di un gruppo")
        print("0) Torna al menu principale")

        try:
            scelta = input("\nScegli un'opzione: ").strip()

            if scelta == "1":
                # Passa l'ID istanza per utilizzare una sessione dedicata
                await get_all_user_groups(instance_id)
                selected = select_group_for_action()
                if not selected:
                    print("❌ Nessun gruppo selezionato.")
            elif scelta == "2":
                # Passa l'ID istanza per utilizzare una sessione dedicata
                await get_all_user_groups(instance_id)
                selected = select_group_for_action()
                if selected:
                    await download_group_archive(selected, instance_id)
            elif scelta == "0":
                return
            else:
                print("❌ Scelta non valida.")
        except Exception as e:
            log_error(f"Errore nel menu archivio: {e}")
            print("❌ Si è verificato un errore. Riprova.")

def user_menu():
    """Menu per la gestione degli utenti."""
    while True:
        print("\n==== Menu Utenti ====")
        print("1) Aggiungi nuovo utente")
        print("2) Rimuovi utente")
        print("3) Mostra utenti salvati")
        print("0) Torna al menu principale")

        try:
            scelta = input("\nScegli un'opzione: ").strip()

            if scelta == "1":
                add_new_user()
            elif scelta == "2":
                remove_user()
            elif scelta == "3":
                show_saved_users()
            elif scelta == "0":
                return
            else:
                print("❌ Scelta non valida.")
        except Exception as e:
            log_error(f"Errore nel menu utenti: {e}")
            print("❌ Si è verificato un errore. Riprova.")

def group_menu(instance_id):
    """Menu per la gestione dei gruppi."""
    while True:
        print("\n==== Menu Gruppi ====")
        print("1) Mostra gruppi disponibili")
        print("2) Recupera link di un gruppo tramite ID")
        print("0) Torna al menu principale")

        try:
            scelta = input("\nScegli un'opzione: ").strip()

            if scelta == "1":
                # Passa l'ID istanza per utilizzare una sessione dedicata
                asyncio.run(get_all_user_groups(instance_id))
            elif scelta == "2":
                chat_id = input("Inserisci il chat_id del gruppo (es. -1001234567890): ").strip()
                # Passa l'ID istanza per utilizzare una sessione dedicata
                asyncio.run(get_group_link(int(chat_id), instance_id))
            elif scelta == "0":
                return
            else:
                print("❌ Scelta non valida.")
        except ValueError:
            print("❌ L'ID del gruppo deve essere un numero.")
        except Exception as e:
            log_error(f"Errore nel menu gruppi: {e}")
            print("❌ Si è verificato un errore. Riprova.")

def is_instance_monitoring(instance_id, lock_file):
    """Controlla se l'istanza sta già eseguendo il monitoraggio."""
    instances = check_running_instances(lock_file)
    this_instance = instances.get(instance_id, {})
    return this_instance.get("monitoring", False)

def set_instance_monitoring_state(instance_id, lock_file, state):
    """Imposta lo stato di monitoraggio dell'istanza."""
    from utils import acquire_lock, release_lock, load_json, save_json
    
    if not acquire_lock(lock_file, instance_id):
        return False
    
    try:
        instances = load_json(lock_file)
        if instance_id in instances:
            instances[instance_id]["monitoring"] = state
            save_json(lock_file, instances)
            return True
        return False
    finally:
        release_lock(lock_file, instance_id)

def main_menu(instance_id):
    """Menu principale."""
    while True:
        try:
            print("\n======== Telegram Media Downloader ========")
            print(f"🆔 Istanza: {instance_id}")
            
            # Controlla se questa istanza sta già eseguendo il monitoraggio
            monitoring_state = is_instance_monitoring(instance_id, LOCK_FILE)
            if monitoring_state:
                print("🔄 Stato: Monitoraggio attivo")
            else:
                print("🔄 Stato: In attesa")
                
            print("1) Gestione Utenti")
            print("2) Gestione Gruppi")
            print("3) Gestione Archivi")
            print("4) Mostra istanze attive")
            print("5) Avvia monitoraggio")
            print("0) Esci")

            scelta = input("\nScegli un'opzione: ").strip()

            if scelta == "1":
                user_menu()
            elif scelta == "2":
                group_menu(instance_id)
            elif scelta == "3":
                asyncio.run(archive_menu(instance_id))
            elif scelta == "4":
                show_running_instances()
            elif scelta == "5":
                if monitoring_state:
                    print("⚠️ Questa istanza sta già eseguendo il monitoraggio.")
                    continue
                    
                print("\n🔄 Avvio monitoraggio...")
                
                # Imposta lo stato di monitoraggio a True
                set_instance_monitoring_state(instance_id, LOCK_FILE, True)
                
                try:
                    asyncio.run(start_monitoring(instance_id))
                except KeyboardInterrupt:
                    print("\n🛑 Monitoraggio interrotto manualmente.")
                except Exception as e:
                    log_error(f"Errore durante il monitoraggio: {e}")
                    print(f"❌ Errore durante il monitoraggio: {e}")
                finally:
                    # Reimposta lo stato di monitoraggio a False
                    set_instance_monitoring_state(instance_id, LOCK_FILE, False)
                    # Pulisci i file di sessione temporanei
                    cleanup_session_files(instance_id)
            elif scelta == "0":
                print("👋 Uscita...")
                # Pulisci i file di sessione temporanei prima di uscire
                cleanup_session_files(instance_id)
                unregister_instance(instance_id, LOCK_FILE)
                sys.exit(0)
            else:
                print("❌ Scelta non valida.")
        except KeyboardInterrupt:
            print("\n⚠️ Operazione interrotta. Tornando al menu principale...")
        except Exception as e:
            log_error(f"Errore nel menu principale: {e}")
            print("❌ Si è verificato un errore. Riprova.")

if __name__ == "__main__":
    # Genera un ID univoco per questa istanza
    instance_id = get_instance_id()
    
    # Aggiungi un piccolo ritardo casuale per evitare conflitti all'avvio
    time.sleep(random.uniform(0.1, 0.5))
    
    # Registra l'istanza
    if not register_instance(instance_id, LOCK_FILE):
        print("❌ Impossibile registrare l'istanza. Controlla i log per maggiori dettagli.")
        sys.exit(1)
    
    try:
        print(f"\n🚀 Avvio Telegram Media Downloader [Istanza: {instance_id}]")
        print("💡 Puoi eseguire più istanze contemporaneamente per operazioni diverse.")
        
        main_menu(instance_id)
    except KeyboardInterrupt:
        print("\n🛑 Programma interrotto manualmente.")
    except Exception as e:
        log_error(f"Errore non gestito: {e}")
        print(f"\n❌ Errore: {e}")
    finally:
        # Pulisci i file di sessione prima di uscire
        cleanup_session_files(instance_id)
        # Rimuovi questa istanza dal registro
        unregister_instance(instance_id, LOCK_FILE)