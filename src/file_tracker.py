"""
File Tracker Module

Tracks file read positions for incremental reading.
On startup, records current file sizes as baseline (no historical processing).
On changes, reads only new content with overlap for pattern continuity.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime

from .config import config


class FileTracker:
    """
    Tracks file positions to enable incremental reading.
    
    Key features:
    - On first encounter: Records current size as baseline (skips existing content)
    - On subsequent reads: Only reads NEW bytes with overlap
    - Overlap ensures we don't miss patterns split across reads
    """
    
    def __init__(self):
        # {filepath: last_byte_position}
        self._positions: Dict[str, int] = {}
        # Track when we started monitoring each file
        self._start_times: Dict[str, datetime] = {}
    
    def initialize_file(self, filepath: str) -> None:
        """
        Initialize tracking for a file.
        Sets baseline to current file size (won't process existing content).
        """
        if filepath in self._positions:
            return  # Already tracking
        
        try:
            current_size = os.path.getsize(filepath)
            self._positions[filepath] = current_size
            self._start_times[filepath] = datetime.now()
            print(f"[TRACKER] Initialized {Path(filepath).parent.name}/...json at position {current_size:,} bytes")
        except OSError as e:
            print(f"[TRACKER] Error initializing {filepath}: {e}")
    
    def get_new_content(self, filepath: str) -> Optional[Tuple[str, int, int]]:
        """
        Read new content from file with overlap.
        
        Returns:
            Tuple of (content, read_start_position, last_known_position) or None if no new content
            - content: The string content read from file
            - read_start_position: Absolute position where this read started
            - last_known_position: The position we had before this read (for determining "new" patterns)
        """
        try:
            current_size = os.path.getsize(filepath)
        except OSError as e:
            print(f"[TRACKER] Error getting file size for {filepath}: {e}")
            return None
        
        # First encounter - initialize and skip
        if filepath not in self._positions:
            self.initialize_file(filepath)
            return None
        
        last_position = self._positions[filepath]
        
        # No new content
        if current_size <= last_position:
            return None
        
        # Calculate how much to read
        new_bytes = current_size - last_position
        bytes_to_read = min(new_bytes + config.OVERLAP_BYTES, config.MAX_READ_BYTES)
        
        # Read with overlap (go back OVERLAP_BYTES from last_position)
        read_start = max(0, last_position - config.OVERLAP_BYTES)
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(read_start)
                content = f.read(bytes_to_read)
            
            # Update position to current size
            self._positions[filepath] = current_size
            
            return (content, read_start, last_position)
            
        except OSError as e:
            print(f"[TRACKER] Error reading {filepath}: {e}")
            return None
        except UnicodeDecodeError as e:
            print(f"[TRACKER] Unicode decode error in {filepath}: {e}")
            return None
    
    def is_new_file(self, filepath: str) -> bool:
        """Check if this file hasn't been seen before."""
        return filepath not in self._positions
    
    def get_tracked_count(self) -> int:
        """Get number of files being tracked."""
        return len(self._positions)
    
    def get_position(self, filepath: str) -> Optional[int]:
        """Get current tracked position for a file."""
        return self._positions.get(filepath)


# Singleton instance
file_tracker = FileTracker()
