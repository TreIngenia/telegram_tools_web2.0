import os
import sys
import subprocess
import time
import platform
from config import LOCK_FILE
from utils import load_json, check_running_instances, unregister_instance, is_process_running, log_error

def start_new_instance():
    """Avvia una nuova istanza del programma."""
    current_script = sys.argv[0]
    
    try:
        # Avvia un nuovo processo con lo stesso script
        if platform.system().lower() == 'windows':
            # Su Windows, usa subprocess.CREATE_NO_WINDOW per evitare finestre del terminale
            process = subprocess.Popen(
                [sys.executable, current_script],
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                creationflags=subprocess.CREATE_NO_WINDOW,
                start_new_session=True
            )
        else:
            # Su Linux/macOS
            process = subprocess.Popen(
                [sys.executable, current_script], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                start_new_session=True
            )
        
        # Verifica che il processo sia stato avviato correttamente
        if process.poll() is None:  # None significa che è in esecuzione
            print("✅ Nuova istanza avviata correttamente.")
            # Attendi un momento per permettere al processo di inizializzarsi
            time.sleep(1)
            return True
        else:
            print(f"❌ Errore: il processo è terminato immediatamente con codice {process.returncode}")
            return False
    except Exception as e:
        log_error(f"Errore nell'avvio di una nuova istanza: {e}")
        return False

def kill_instance(instance_id=None):
    """Termina un'istanza specifica o tutte le istanze."""
    try:
        instances = check_running_instances(LOCK_FILE)
        
        if not instances:
            print("❌ Nessuna istanza attiva da terminare.")
            return False
        
        if instance_id:
            # Termina solo l'istanza specificata
            if instance_id in instances:
                pid = instances[instance_id].get('pid')
                try:
                    if is_process_running(pid):
                        # Termina il processo in modo cross-platform
                        if platform.system().lower() == 'windows':
                            # Su Windows, usa taskkill
                            subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                          stderr=subprocess.PIPE, 
                                          stdout=subprocess.PIPE,
                                          creationflags=subprocess.CREATE_NO_WINDOW)
                        else:
                            # Su Linux/macOS
                            os.kill(pid, 9)  # SIGKILL
                            
                        # Rimuovi l'istanza dal registro
                        unregister_instance(instance_id, LOCK_FILE)
                        print(f"✅ Istanza {instance_id} (PID: {pid}) terminata.")
                        return True
                    else:
                        print(f"⚠️ L'istanza {instance_id} risulta già terminata.")
                        unregister_instance(instance_id, LOCK_FILE)
                        return True
                except Exception as e:
                    print(f"❌ Impossibile terminare l'istanza {instance_id}: {e}")
                    # Rimuovi comunque dal registro se il processo non esiste più
                    if not is_process_running(pid):
                        unregister_instance(instance_id, LOCK_FILE)
                    return False
            else:
                print(f"❌ Istanza {instance_id} non trovata.")
                return False
        else:
            # Mostra elenco istanze e chiedi quale terminare
            print("\n📋 Istanze attive:")
            instance_ids = list(instances.keys())
            for i, inst_id in enumerate(instance_ids, 1):
                info = instances[inst_id]
                print(f"{i}. ID: {inst_id} | PID: {info.get('pid')} | Avviato: {info.get('start_time')}")
            
            try:
                choice = input("\nInserisci il numero dell'istanza da terminare (0 per annullare): ").strip()
                
                if not choice or choice == "0":
                    return False
                    
                choice = int(choice)
                if 1 <= choice <= len(instance_ids):
                    selected_id = instance_ids[choice - 1]
                    return kill_instance(selected_id)
                else:
                    print("❌ Scelta non valida.")
                    return False
            except ValueError:
                print("❌ Inserisci un numero valido.")
                return False
            except Exception as e:
                log_error(f"Errore durante la terminazione dell'istanza: {e}")
                return False
    except Exception as e:
        log_error(f"Errore nella gestione delle istanze: {e}")
        return False

def show_running_instances():
    """Mostra le istanze attualmente in esecuzione."""
    try:
        instances = check_running_instances(LOCK_FILE)
        
        if not instances:
            print("📊 Nessuna istanza attiva al momento.")
            return
        
        print("\n📊 Istanze attive:")
        for i, (instance_id, info) in enumerate(instances.items(), 1):
            print(f"{i}. ID: {instance_id} | PID: {info.get('pid')} | Avviato: {info.get('start_time')}")
    except Exception as e:
        log_error(f"Errore durante la visualizzazione delle istanze: {e}")
        print("❌ Si è verificato un errore durante la visualizzazione delle istanze.")

def multiinstance_menu():
    """Menu per la gestione delle istanze multiple."""
    while True:
        print("\n==== Gestione Istanze Multiple ====")
        print("1) Mostra istanze attive")
        print("2) Avvia nuova istanza")
        print("3) Termina istanza")
        print("0) Esci")
        
        try:
            choice = input("\nScegli un'opzione: ").strip()
            
            if choice == "1":
                show_running_instances()
            
            elif choice == "2":
                start_new_instance()
                print("⚠️ Aspetta qualche secondo prima di avviare altre istanze.")
                time.sleep(2)  # Attesa per evitare problemi di concorrenza
            
            elif choice == "3":
                kill_instance()
            
            elif choice == "0":
                return
            
            else:
                print("❌ Scelta non valida.")
        except Exception as e:
            log_error(f"Errore nel menu di gestione istanze: {e}")
            print("❌ Si è verificato un errore. Riprova.")
            time.sleep(1)

if __name__ == "__main__":
    print("⚠️ Questo script non dovrebbe essere eseguito direttamente.")
    print("   Usa app.py per avviare il programma.")