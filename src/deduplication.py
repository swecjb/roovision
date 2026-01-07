"""
Deduplication Module

Tracks processed subtask IDs to prevent duplicate changelog entries.
Implements log rotation when files exceed size limit.
"""

import os
from pathlib import Path
from typing import Set
from datetime import datetime

from .config import config


class DeduplicationManager:
    """
    Manages processed subtask IDs with persistent storage and log rotation.
    
    Log file format:
    - One subtask ID per line
    - Format: {subtask_id}|{timestamp}
    
    Rotation:
    - When main log exceeds MAX_LOG_FILE_SIZE_BYTES
    - .log -> .log.1 -> .log.2 -> .log.3 (deleted)
    """
    
    def __init__(self):
        self._processed_ids: Set[str] = set()
        self._log_file = Path(config.PROCESSED_IDS_LOG_PATH) / 'processed_ids.log'
        self._load_existing_ids()
    
    def _load_existing_ids(self) -> None:
        """Load all processed IDs from log files into memory."""
        log_dir = Path(config.PROCESSED_IDS_LOG_PATH)
        
        # Load from all rotated log files
        log_files = [
            log_dir / 'processed_ids.log',
            log_dir / 'processed_ids.log.1',
            log_dir / 'processed_ids.log.2',
        ]
        
        for log_file in log_files:
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and '|' in line:
                                subtask_id = line.split('|')[0]
                                self._processed_ids.add(subtask_id)
                            elif line:
                                # Legacy format without timestamp
                                self._processed_ids.add(line)
                except OSError as e:
                    print(f"[DEDUP] Warning: Could not load {log_file}: {e}")
        
        print(f"[DEDUP] Loaded {len(self._processed_ids)} previously processed IDs")
    
    def is_processed(self, subtask_id: str) -> bool:
        """Check if a subtask ID has already been processed."""
        return subtask_id in self._processed_ids
    
    def mark_processed(self, subtask_id: str) -> None:
        """Mark a subtask ID as processed and persist to log."""
        if subtask_id in self._processed_ids:
            return
        
        self._processed_ids.add(subtask_id)
        
        # Append to log file
        timestamp = datetime.now().isoformat()
        log_entry = f"{subtask_id}|{timestamp}\n"
        
        try:
            # Ensure directory exists
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            # Check if rotation is needed
            self._check_rotation()
            
        except OSError as e:
            print(f"[DEDUP] Error writing to log: {e}")
    
    def _check_rotation(self) -> None:
        """Check if log rotation is needed and perform it."""
        if not self._log_file.exists():
            return
        
        try:
            file_size = self._log_file.stat().st_size
            
            if file_size >= config.MAX_LOG_FILE_SIZE_BYTES:
                self._rotate_logs()
                
        except OSError as e:
            print(f"[DEDUP] Error checking log size: {e}")
    
    def _rotate_logs(self) -> None:
        """Perform log rotation."""
        log_dir = self._log_file.parent
        base_name = 'processed_ids.log'
        
        print(f"[DEDUP] Rotating logs (current size: {self._log_file.stat().st_size:,} bytes)")
        
        try:
            # Delete oldest if exists (.log.{LOG_ROTATION_COUNT})
            oldest = log_dir / f"{base_name}.{config.LOG_ROTATION_COUNT}"
            if oldest.exists():
                oldest.unlink()
                print(f"[DEDUP] Deleted {oldest.name}")
            
            # Shift existing rotated logs
            for i in range(config.LOG_ROTATION_COUNT - 1, 0, -1):
                current = log_dir / f"{base_name}.{i}"
                next_name = log_dir / f"{base_name}.{i + 1}"
                if current.exists():
                    current.rename(next_name)
            
            # Rotate current log to .1
            rotated = log_dir / f"{base_name}.1"
            self._log_file.rename(rotated)
            print(f"[DEDUP] Rotated {base_name} -> {rotated.name}")
            
            # Create fresh log file
            self._log_file.touch()
            
        except OSError as e:
            print(f"[DEDUP] Error during rotation: {e}")
    
    def get_processed_count(self) -> int:
        """Get count of processed subtask IDs."""
        return len(self._processed_ids)


# Singleton instance
dedup_manager = DeduplicationManager()
