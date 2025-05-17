"""
Utility per tenere traccia dei client attivi e diagnosticare problemi di disconnessione.

Questo modulo implementa un sistema di tracciamento globale per tutti i client Telegram
che vengono creati nell'applicazione, permettendo di identificare e risolvere
problemi di disconnessione involontaria.
"""

import weakref
import threading
import time
from datetime import datetime

# Dizionario che traccia tutti i client attivi
# Utilizziamo weakref.WeakValueDictionary per non impedire la garbage collection
active_clients = weakref.WeakValueDictionary()
client_operations = {}  # Mappa client_id -> operation_info
client_lock = threading.RLock()  # Lock per sincronizzare l'accesso ai dizionari

def register_client(client, operation_type, nickname, operation_id=None):
    """
    Registra un nuovo client nel sistema di tracciamento.
    
    Args:
        client: Il client Telegram da registrare
        operation_type: Tipo di operazione (es. "monitoring", "download")
        nickname: Nickname dell'utente associato
        operation_id: ID dell'operazione associata (se disponibile)
    
    Returns:
        client_id: L'ID univoco del client registrato
    """
    client_id = id(client)
    
    with client_lock:
        active_clients[client_id] = client
        client_operations[client_id] = {
            "operation_type": operation_type,
            "nickname": nickname,
            "operation_id": operation_id,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active"
        }
    
    print(f"[TRACCIAMENTO] Client registrato: {client_id} - {operation_type} - {nickname}")
    return client_id

def unregister_client(client):
    """
    Rimuove un client dal sistema di tracciamento.
    
    Args:
        client: Il client Telegram da rimuovere
    """
    client_id = id(client)
    
    with client_lock:
        if client_id in active_clients:
            del active_clients[client_id]
        
        if client_id in client_operations:
            operation_info = client_operations[client_id]
            print(f"[TRACCIAMENTO] Client rimosso: {client_id} - {operation_info['operation_type']} - {operation_info['nickname']}")
            operation_info["status"] = "disconnected"
            operation_info["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_active_clients():
    """
    Restituisce informazioni su tutti i client attualmente attivi.
    
    Returns:
        clients_info: Lista di dizionari con informazioni sui client attivi
    """
    clients_info = []
    
    with client_lock:
        for client_id, client in active_clients.items():
            if client_id in client_operations:
                info = client_operations[client_id].copy()
                info["client_id"] = client_id
                info["is_connected"] = client.is_connected()
                clients_info.append(info)
    
    return clients_info

def print_client_status():
    """Stampa lo stato di tutti i client attivi."""
    clients = get_active_clients()
    
    print("\n======== CLIENT ATTIVI ========")
    if not clients:
        print("Nessun client attivo")
        return
    
    for client in clients:
        print(f"ID: {client['client_id']}")
        print(f"  Tipo: {client['operation_type']}")
        print(f"  Utente: {client['nickname']}")
        print(f"  Operazione: {client['operation_id']}")
        print(f"  Avviato: {client['start_time']}")
        print(f"  Stato: {'Connesso' if client['is_connected'] else 'Disconnesso'}")
        print("--------------------------")

def debug_client_operations(client_id=None):
    """
    Fornisce informazioni dettagliate sulle operazioni associate ai client.
    
    Args:
        client_id: Se specificato, mostra solo le informazioni per questo client
    """
    with client_lock:
        if client_id:
            if client_id in client_operations:
                print(f"\n==== Dettagli per client {client_id} ====")
                for key, value in client_operations[client_id].items():
                    print(f"{key}: {value}")
            else:
                print(f"Client {client_id} non trovato nel registro operazioni")
        else:
            print("\n==== Registro operazioni client ====")
            for cid, info in client_operations.items():
                is_active = cid in active_clients
                print(f"Client {cid} - Attivo: {is_active}")
                for key, value in info.items():
                    print(f"  {key}: {value}")
                print("---")