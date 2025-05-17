import os
import shutil
import random
import time
import threading
import uuid

class SessionManager:
    """Gestisce le sessioni per evitare conflitti all'interno della stessa istanza."""
    
    def __init__(self):
        self.active_sessions = {}  # {operation_id: {nickname: session_path}}
        self.mutex = threading.Lock()
    
    def create_session(self, nickname, operation_type):
        """
        Crea una sessione unica per un'operazione specifica.
        
        Args:
            nickname: Il nickname dell'utente
            operation_type: Il tipo di operazione (monitoraggio, download, ecc.)
            
        Returns:
            operation_id: ID univoco per l'operazione
            session_path: Percorso della sessione senza estensione .session
        """
        with self.mutex:
            # Crea un ID univoco per l'operazione
            operation_id = f"{operation_type}_{str(uuid.uuid4())[:8]}_{int(time.time())}"
            
            # Sessione originale
            original_session = f'session_{nickname}.session'
            
            # Crea una sessione dedicata per questa operazione
            session_path = f'session_{nickname}_{operation_id}'
            session_file = f'{session_path}.session'
            
            # Copia il file di sessione originale se esiste
            if os.path.exists(original_session):
                try:
                    shutil.copy2(original_session, session_file)
                except Exception as e:
                    print(f"Avviso: Impossibile copiare il file di sessione: {e}")
                    # Caso fallback: usa un percorso univoco ma lascia che Telethon lo crei
            
            # Memorizza la sessione attiva
            if operation_id not in self.active_sessions:
                self.active_sessions[operation_id] = {}
            
            self.active_sessions[operation_id][nickname] = session_path
            
            return operation_id, session_path
    
    def release_session(self, operation_id, nickname=None):
        """
        Rilascia una sessione dopo che l'operazione è completata.
        
        Args:
            operation_id: ID dell'operazione
            nickname: Se specificato, rilascia solo la sessione per questo nickname
        """
        with self.mutex:
            if operation_id not in self.active_sessions:
                return
            
            if nickname:
                # Rilascia solo la sessione specifica
                if nickname in self.active_sessions[operation_id]:
                    session_path = self.active_sessions[operation_id][nickname]
                    session_file = f'{session_path}.session'
                    
                    # Rimuovi il file se esiste
                    if os.path.exists(session_file):
                        try:
                            os.remove(session_file)
                        except Exception as e:
                            print(f"Avviso: Impossibile rimuovere il file di sessione: {e}")
                    
                    # Rimuovi eventuali file correlati
                    for ext in ['.session-journal', '-journal']:
                        related_file = f'{session_path}{ext}'
                        if os.path.exists(related_file):
                            try:
                                os.remove(related_file)
                            except:
                                pass
                    
                    # Rimuovi dalla mappa
                    del self.active_sessions[operation_id][nickname]
            else:
                # Rilascia tutte le sessioni per questa operazione
                for nick, session_path in self.active_sessions[operation_id].items():
                    session_file = f'{session_path}.session'
                    
                    # Rimuovi il file se esiste
                    if os.path.exists(session_file):
                        try:
                            os.remove(session_file)
                        except Exception as e:
                            print(f"Avviso: Impossibile rimuovere il file di sessione: {e}")
                    
                    # Rimuovi eventuali file correlati
                    for ext in ['.session-journal', '-journal']:
                        related_file = f'{session_path}{ext}'
                        if os.path.exists(related_file):
                            try:
                                os.remove(related_file)
                            except:
                                pass
                
                # Rimuovi l'intera operazione
                del self.active_sessions[operation_id]
    
    def get_session_path(self, operation_id, nickname):
        """
        Ottiene il percorso della sessione per un'operazione e un nickname.
        
        Args:
            operation_id: ID dell'operazione
            nickname: Nickname dell'utente
            
        Returns:
            Percorso della sessione o None se non trovato
        """
        with self.mutex:
            if operation_id in self.active_sessions and nickname in self.active_sessions[operation_id]:
                return self.active_sessions[operation_id][nickname]
            return None
    
    def cleanup_all(self):
        """Pulisce tutte le sessioni attive."""
        with self.mutex:
            for operation_id in list(self.active_sessions.keys()):
                self.release_session(operation_id)

# Creazione di un'istanza singleton
session_manager = SessionManager()