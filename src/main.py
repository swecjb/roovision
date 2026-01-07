#!/usr/bin/env python3
"""
Roovision - Main Entry Point

Automated changelog extraction for Roo Code's Orchestrator mode.
Monitors conversation history files and extracts completed subtask
instructions + results into timestamped markdown files.

Usage:
    python src/main.py

The script runs continuously, watching for new subtask completions.
Press Ctrl+C to stop.

https://github.com/yourusername/roovision
"""

import sys
import signal
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.file_tracker import file_tracker
from src.parser import parser
from src.deduplication import dedup_manager
from src.writer import changelog_writer
from src.watcher import TaskFolderWatcher


class ChangelogProcessor:
    """
    Main processor that coordinates all components.
    """
    
    def __init__(self):
        self._watcher = None
        self._running = False
        self._stats = {
            'files_processed': 0,
            'subtasks_found': 0,
            'changelogs_created': 0,
            'duplicates_skipped': 0,
            'ask_mode_skipped': 0,
            'errors': 0
        }
    
    def process_file(self, filepath: str) -> None:
        """
        Process a changed conversation history file.
        Called by the watcher when a file is ready (after debounce).
        """
        self._stats['files_processed'] += 1
        
        # Get new content with overlap
        result = file_tracker.get_new_content(filepath)
        
        if result is None:
            return  # No new content or first initialization
        
        content, read_start, last_position = result
        
        # Find all complete subtask entries in the new content
        # Pass filepath so parser can read more of the file if instruction isn't in buffer
        entries = parser.find_all_complete_subtasks(content, read_start, last_position, filepath)
        
        if not entries:
            return
        
        self._stats['subtasks_found'] += len(entries)
        
        # Process each entry
        for entry in entries:
            # Check for duplicates
            if dedup_manager.is_processed(entry.subtask_id):
                print(f"[MAIN] Skipping duplicate: {entry.subtask_id}")
                self._stats['duplicates_skipped'] += 1
                continue
            
            # Skip ask-mode subtasks if configured (they don't make code changes)
            if config.SKIP_ASK_MODE and entry.mode == 'ask':
                print(f"[MAIN] Skipping ask-mode subtask: {entry.subtask_id}")
                dedup_manager.mark_processed(entry.subtask_id)  # Mark to avoid re-processing
                self._stats['ask_mode_skipped'] += 1
                continue
            
            # Write changelog
            output_path = changelog_writer.write_changelog(entry)
            
            if output_path:
                # Mark as processed
                dedup_manager.mark_processed(entry.subtask_id)
                self._stats['changelogs_created'] += 1
                print(f"[MAIN] ✓ Changelog created for subtask {entry.subtask_id}")
            else:
                self._stats['errors'] += 1
                print(f"[MAIN] ✗ Failed to create changelog for {entry.subtask_id}")
    
    def initialize_file(self, filepath: str) -> None:
        """
        Initialize tracking for an existing file without processing it.
        Called at startup to set baselines.
        """
        file_tracker.initialize_file(filepath)
    
    def start(self) -> bool:
        """
        Start the changelog processor.
        
        Returns:
            True if started successfully
        """
        print()
        print("=" * 60)
        print("  Roovision 🔭")
        print("  Automated changelog extraction for Roo Code")
        print("=" * 60)
        print()
        
        # Print and validate configuration
        config.print_config()
        print()
        
        if not config.validate():
            print("[MAIN] Configuration validation failed!")
            return False
        
        # Ensure output directories exist
        config.ensure_directories()
        print(f"[MAIN] Output directory: {config.CHANGELOG_OUTPUT_PATH}")
        print(f"[MAIN] Logs directory: {config.PROCESSED_IDS_LOG_PATH}")
        print(f"[MAIN] Previously processed IDs: {dedup_manager.get_processed_count()}")
        print()
        
        # Create watcher
        self._watcher = TaskFolderWatcher(self.process_file)
        
        # Initialize existing files (set baselines, don't process)
        print("[MAIN] Initializing existing files...")
        self._watcher.initialize_existing_files(self.initialize_file)
        print(f"[MAIN] Tracking {file_tracker.get_tracked_count()} files")
        print()
        
        # Start watching
        if not self._watcher.start():
            print("[MAIN] Failed to start watcher!")
            return False
        
        self._running = True
        print("[MAIN] ✓ Roovision started successfully!")
        print("[MAIN] Watching for new subtask completions...")
        print("[MAIN] Press Ctrl+C to stop")
        print()
        
        return True
    
    def stop(self):
        """Stop the changelog processor."""
        self._running = False
        
        if self._watcher:
            self._watcher.stop()
        
        print()
        print("=" * 60)
        print("  Roovision Stopped")
        print("=" * 60)
        self.print_stats()
    
    def print_stats(self):
        """Print processing statistics."""
        print()
        print("Session Statistics:")
        print(f"  Files processed:     {self._stats['files_processed']}")
        print(f"  Subtasks found:      {self._stats['subtasks_found']}")
        print(f"  Changelogs created:  {self._stats['changelogs_created']}")
        print(f"  Duplicates skipped:  {self._stats['duplicates_skipped']}")
        print(f"  Ask-mode skipped:    {self._stats['ask_mode_skipped']}")
        print(f"  Errors:              {self._stats['errors']}")
        print()
    
    def run_forever(self):
        """Run until stopped by signal."""
        while self._running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break
        
        self.stop()


def main():
    """Main entry point."""
    processor = ChangelogProcessor()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\n[MAIN] Shutdown signal received...")
        processor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the processor
    if not processor.start():
        print("[MAIN] Failed to start. Exiting.")
        sys.exit(1)
    
    # Run until stopped
    processor.run_forever()


if __name__ == '__main__':
    main()
