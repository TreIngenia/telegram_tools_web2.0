"""
Wrapper per i client Telethon che gestisce in modo sicuro le disconnessioni.
"""

import asyncio
import signal
import threading
import time
from telethon import TelegramClient
from telethon.errors import ServerError, TimedOutError, FloodWaitError

class SafeTelegramClient:
    """
    Wrapper per TelegramClient che gestisce meglio le disconnessioni e la chiusura.
    Impedisce gli errori di connessione quando l'applicazione viene chiusa.
    """
    
    def __init__(self, session_path, api_id, api_hash, **kwargs):
        self.session_path = session_path
        self.api_id = api_id
        self.api_hash = api_hash
        self.kwargs = kwargs
        self.client = None
        self._is_connected = False
        self._disconnect_event = threading.Event()
        self._client_lock = threading.RLock()
        
    async def start(self, phone=None):
        """Avvia il client in modo sicuro."""
        if self.client is None:
            with self._client_lock:
                self.client = TelegramClient(
                    self.session_path,
                    self.api_id,
                    self.api_hash,
                    **self.kwargs
                )
        
        if not self._is_connected:
            await self.client.start(phone)
            self._is_connected = True
            self._disconnect_event.clear()
        
        return self
    
    async def disconnect(self):
        """Disconnette il client in modo sicuro."""
        self._disconnect_event.set()
        
        if self.client and self._is_connected:
            try:
                # Imposta un timeout per la disconnessione
                disconnection_task = asyncio.create_task(self._safe_disconnect())
                
                # Attendi al massimo 3 secondi
                try:
                    await asyncio.wait_for(disconnection_task, timeout=3)
                except asyncio.TimeoutError:
                    print(f"[SafeTelegramClient] Timeout durante la disconnessione, forzando la chiusura")
                    # Non facciamo nulla, permettiamo che il client venga distrutto comunque
            except Exception as e:
                print(f"[SafeTelegramClient] Errore durante la disconnessione: {e}")
            finally:
                self._is_connected = False
                self.client = None
    
    async def _safe_disconnect(self):
        """Implementazione sicura della disconnessione."""
        try:
            # Usa un gestore di eccezioni per assicurarsi che la disconnessione continui
            # anche se ci sono errori di socket o di altro tipo
            try:
                await self.client.disconnect()
            except (ConnectionError, ServerError, TimedOutError, OSError) as e:
                # Questi errori sono attesi durante la disconnessione forzata
                print(f"[SafeTelegramClient] Errore previsto durante la disconnessione: {e}")
                pass
        finally:
            self._is_connected = False
    
    def is_connected(self):
        """Verifica se il client è connesso."""
        if self.client:
            return self._is_connected and self.client.is_connected()
        return False
    
    async def __aenter__(self):
        """Supporto per context manager (async with)."""
        await self.start()
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Supporto per context manager (async with)."""
        await self.disconnect()
    
    def __del__(self):
        """Distruttore per garantire la disconnessione."""
        if self.client and self._is_connected:
            # Tentiamo una disconnessione finale in caso di garbage collection
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.disconnect())
                else:
                    # In caso di loop non in esecuzione, creiamo un nuovo loop temporaneo
                    async def _cleanup():
                        await self.disconnect()
                    
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(_cleanup())
                    loop.close()
            except Exception:
                # Non possiamo fare molto altro qui
                pass