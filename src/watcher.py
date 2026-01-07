"""
Watcher Module

File system watcher using watchdog library.
Monitors Roo Code tasks folder for changes to api_conversation_history.json files.
Implements debouncing to wait for file writes to complete.
"""

import os
import time
import threading
from pathlib import Path
from typing import Callable, Dict, Set
from datetime import datetime, timedelta
from stat import ST_MTIME

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from .config import config


class DebouncedHandler(FileSystemEventHandler):
    """
    File system event handler with debouncing.
    
    Debouncing ensures we don't read a file while it's still being written.
    Waits DEBOUNCE_SECONDS after the last change before triggering callback.
    """
    
    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self._callback = callback
        self._pending: Dict[str, datetime] = {}  # {filepath: last_change_time}
        self._lock = threading.Lock()
        self._running = True
        
        # Start the debounce checker thread
        self._checker_thread = threading.Thread(target=self._debounce_checker, daemon=True)
        self._checker_thread.start()
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        self._handle_file_event(event.src_path)
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        self._handle_file_event(event.src_path)
    
    def _handle_file_event(self, filepath: str):
        """Record a file change event for debouncing."""
        # Only care about api_conversation_history.json files
        if not filepath.endswith(config.CONVERSATION_FILENAME):
            return
        
        with self._lock:
            self._pending[filepath] = datetime.now()
    
    def _debounce_checker(self):
        """Background thread that checks for debounced events ready to process."""
        while self._running:
            ready_files = []
            cutoff_time = datetime.now() - timedelta(seconds=config.DEBOUNCE_SECONDS)
            
            with self._lock:
                # Find files that haven't changed for DEBOUNCE_SECONDS
                for filepath, last_change in list(self._pending.items()):
                    if last_change <= cutoff_time:
                        ready_files.append(filepath)
                        del self._pending[filepath]
            
            # Process ready files outside the lock
            for filepath in ready_files:
                try:
                    self._callback(filepath)
                except Exception as e:
                    print(f"[WATCHER] Error processing {filepath}: {e}")
            
            # Sleep briefly before next check
            time.sleep(0.1)
    
    def stop(self):
        """Stop the debounce checker thread."""
        self._running = False


class TaskFolderWatcher:
    """
    Watches the Roo Code tasks folder for conversation history changes.
    
    Uses watchdog for efficient OS-level file system events (no polling).
    """
    
    def __init__(self, callback: Callable[[str], None]):
        """
        Initialize the watcher.
        
        Args:
            callback: Function to call when a file is ready to process.
                      Receives the full path to the changed file.
        """
        self._watch_path = Path(config.ROO_TASKS_PATH)
        self._callback = callback
        self._handler = DebouncedHandler(callback)
        self._observer = Observer()
        self._started = False
    
    def start(self) -> bool:
        """
        Start watching for file changes.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self._started:
            return True
        
        if not self._watch_path.exists():
            print(f"[WATCHER] Error: Watch path does not exist: {self._watch_path}")
            return False
        
        try:
            # Schedule recursive watch on the tasks folder
            self._observer.schedule(
                self._handler,
                str(self._watch_path),
                recursive=True
            )
            self._observer.start()
            self._started = True
            
            print(f"[WATCHER] Started watching: {self._watch_path}")
            print(f"[WATCHER] Debounce: {config.DEBOUNCE_SECONDS}s")
            
            return True
            
        except Exception as e:
            print(f"[WATCHER] Error starting observer: {e}")
            return False
    
    def stop(self):
        """Stop watching for file changes."""
        if not self._started:
            return
        
        self._handler.stop()
        self._observer.stop()
        self._observer.join(timeout=5)
        self._started = False
        print("[WATCHER] Stopped")
    
    def is_running(self) -> bool:
        """Check if the watcher is running."""
        return self._started and self._observer.is_alive()
    
    def initialize_existing_files(self, init_callback: Callable[[str], None]):
        """
        Initialize tracking for all existing conversation history files.
        This sets baselines so we only process NEW content.
        
        If MAX_FILE_AGE_DAYS is set, only initializes files modified within that period.
        
        Args:
            init_callback: Function to call for each existing file
        """
        if not self._watch_path.exists():
            return
        
        count = 0
        skipped = 0
        
        # Calculate cutoff time if filtering by age
        cutoff_time = None
        if config.MAX_FILE_AGE_DAYS > 0:
            cutoff_time = datetime.now() - timedelta(days=config.MAX_FILE_AGE_DAYS)
            print(f"[WATCHER] Filtering files modified after: {cutoff_time.strftime('%Y-%m-%d %H:%M')}")
        
        for json_file in self._watch_path.rglob(config.CONVERSATION_FILENAME):
            try:
                # Check file age if filtering is enabled
                if cutoff_time is not None:
                    file_mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        skipped += 1
                        continue
                
                init_callback(str(json_file))
                count += 1
            except Exception as e:
                print(f"[WATCHER] Error initializing {json_file}: {e}")
        
        if skipped > 0:
            print(f"[WATCHER] Skipped {skipped} files older than {config.MAX_FILE_AGE_DAYS} days")
        print(f"[WATCHER] Initialized {count} recent conversation files")
