"""
Gestione sicura della terminazione dell'applicazione.

Questo modulo fornisce funzioni per terminare in modo pulito l'applicazione,
gestendo correttamente tutte le risorse, thread e connessioni attive.
"""

import os
import sys
import time
import signal
import threading
import asyncio
import traceback
from PyQt5.QtWidgets import QApplication, QProgressDialog, QMessageBox
from PyQt5.QtCore import Qt

# Importa il session manager
from gui_session_manager import session_manager

def force_terminate(exit_code=1, timeout=2):
    """
    Forza la terminazione del processo dopo un timeout.
    Utile quando ci sono thread o connessioni bloccate.
    
    Args:
        exit_code: Codice di uscita da utilizzare
        timeout: Tempo di attesa in secondi prima della terminazione forzata
    """
    print(f"Terminazione forzata programmata tra {timeout} secondi...")
    
    def _force_exit():
        time.sleep(timeout)
        print("Terminazione forzata in corso!")
        os._exit(exit_code)
    
    # Crea un thread daemon che terminerà il processo dopo il timeout
    force_thread = threading.Thread(target=_force_exit)
    force_thread.daemon = True
    force_thread.start()

def terminate_application(app, instance_id, lock_file, monitoring_thread=None, operation_threads=None):
    """
    Termina l'applicazione in modo pulito, gestendo tutte le risorse.
    
    Args:
        app: L'istanza QApplication
        instance_id: ID dell'istanza corrente
        lock_file: Percorso del file di lock
        monitoring_thread: Thread di monitoraggio attivo (opzionale)
        operation_threads: Dizionario di thread operativi attivi (opzionale)
    """
    from utils import unregister_instance
    
    # Programma la terminazione forzata come fallback
    force_terminate(exit_code=1, timeout=10)
    
    try:
        # Crea un dialogo modale di avanzamento
        progress = QProgressDialog("Chiusura dell'applicazione...", None, 0, 5)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Chiusura in corso")
        progress.setCancelButton(None)  # Disattiva il pulsante di annullamento
        progress.setMinimumDuration(0)  # Mostra immediatamente
        progress.show()
        QApplication.processEvents()
        
        # 1. Termina i thread di monitoraggio
        progress.setLabelText("Interruzione del monitoraggio...")
        progress.setValue(1)
        QApplication.processEvents()
        
        if monitoring_thread and monitoring_thread.isRunning():
            try:
                monitoring_thread.stop()
                monitoring_thread.wait(3000)  # Attendi max 3 secondi
                if monitoring_thread.isRunning():
                    monitoring_thread.terminate()
            except Exception as e:
                print(f"Errore durante l'interruzione del monitoraggio: {e}")
        
        # 2. Termina gli altri thread operativi
        progress.setLabelText("Interruzione delle operazioni in corso...")
        progress.setValue(2)
        QApplication.processEvents()
        
        if operation_threads:
            for thread_id, thread in list(operation_threads.items()):
                if thread.isRunning():
                    try:
                        thread.terminate()
                        thread.wait(1000)  # Attendi max 1 secondo
                    except Exception as e:
                        print(f"Errore durante l'interruzione del thread {thread_id}: {e}")
        
        # 3. Pulisci tutte le sessioni
        progress.setLabelText("Pulizia delle sessioni...")
        progress.setValue(3)
        QApplication.processEvents()
        
        try:
            session_manager.cleanup_all()
            
            # Pulizia aggiuntiva dei file di sessione
            for file in os.listdir('.'):
                if (file.endswith('.session') and '_' in file) or file.endswith('.session-journal'):
                    try:
                        os.remove(file)
                    except:
                        pass
        except Exception as e:
            print(f"Errore durante la pulizia delle sessioni: {e}")
        
        # 4. Rimuovi l'istanza dal registro
        progress.setLabelText("Rimozione dell'istanza dal registro...")
        progress.setValue(4)
        QApplication.processEvents()
        
        try:
            unregister_instance(instance_id, lock_file)
        except Exception as e:
            print(f"Errore durante la rimozione dell'istanza: {e}")
        
        # 5. Chiudi l'applicazione
        progress.setLabelText("Chiusura completata")
        progress.setValue(5)
        QApplication.processEvents()
        
        # Breve pausa per mostrare il completamento
        time.sleep(0.5)
        
        # Chiudi il dialogo
        progress.close()
        
        print("Terminazione pulita completata")
        
        # Termina il processo
        sys.exit(0)
    except Exception as e:
        print(f"Errore durante la terminazione dell'applicazione: {e}")
        traceback.print_exc()
        
        # In caso di errore, mostra un messaggio e termina forzatamente
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Errore durante la chiusura")
        msg.setText("Si è verificato un errore durante la chiusura dell'applicazione.")
        msg.setDetailedText(str(e) + "\n\n" + traceback.format_exc())
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
        # Termina l'applicazione forzatamente
        os._exit(1)

def setup_signal_handlers(app, instance_id, lock_file):
    """
    Configura i gestori di segnali per garantire una chiusura pulita.
    
    Args:
        app: L'istanza QApplication
        instance_id: ID dell'istanza corrente
        lock_file: Percorso del file di lock
    """
    # Su Windows i segnali sono limitati, ma possiamo gestire SIGINT e SIGTERM
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda s, f: terminate_application(app, instance_id, lock_file))