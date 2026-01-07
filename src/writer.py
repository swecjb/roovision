"""
Writer Module

Handles safe writing of changelog files.
Uses atomic write pattern to prevent corruption.
"""

import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from .config import config
from .formatter import formatter
from .parser import SubtaskEntry


class ChangelogWriter:
    """
    Writes changelog entries to markdown files.
    
    Filename format: changelog_{UTC_TIMESTAMP}_{SUBTASK_ID}.md
    Example: changelog_2026-01-07T11-15-30-123Z_UTC_09d0cb0e-5c00-4df2-90cf-f52c4f85bcfc.md
    """
    
    def __init__(self):
        self._output_dir = Path(config.CHANGELOG_OUTPUT_PATH)
    
    def write_changelog(self, entry: SubtaskEntry) -> Optional[str]:
        """
        Write a changelog entry to a markdown file.
        
        Args:
            entry: SubtaskEntry with subtask_id, mode, instruction, result
            
        Returns:
            Path to created file, or None if failed
        """
        # Generate UTC timestamp for filename and content
        timestamp_utc = datetime.now(timezone.utc)
        
        # Format for content display: ISO format with UTC suffix
        timestamp_display = timestamp_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + ' UTC'
        
        # Create filename-safe timestamp (replace colons with dashes)
        # Format: changelog_YYYY-MM-DDTHH-MM-SS-sss_UTC_subtaskid.md
        filename_timestamp = timestamp_utc.strftime('%Y-%m-%dT%H-%M-%S-%f')[:-3] + '_UTC'
        
        # Build filename: changelog_timestamp_subtaskid.md
        filename = f"changelog_{filename_timestamp}_{entry.subtask_id}.md"
        filepath = self._output_dir / filename
        
        # Format the content
        content = formatter.format_changelog_content(
            subtask_id=entry.subtask_id,
            mode=entry.mode,
            instruction=entry.instruction,
            result=entry.result,
            timestamp=timestamp_display
        )
        
        # Ensure output directory exists
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"[WRITER] Error creating output directory: {e}")
            return None
        
        # Atomic write: write to temp file, then rename
        temp_filepath = filepath.with_suffix('.md.tmp')
        
        try:
            # Write to temp file
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Rename to final filename (atomic on most filesystems)
            temp_filepath.rename(filepath)
            
            print(f"[WRITER] Created changelog: {filename}")
            return str(filepath)
            
        except OSError as e:
            print(f"[WRITER] Error writing changelog: {e}")
            # Clean up temp file if it exists
            if temp_filepath.exists():
                try:
                    temp_filepath.unlink()
                except OSError:
                    pass
            return None
    
    def get_output_directory(self) -> str:
        """Get the configured output directory."""
        return str(self._output_dir)
    
    def get_changelog_count(self) -> int:
        """Count existing changelog files in output directory."""
        if not self._output_dir.exists():
            return 0
        return len(list(self._output_dir.glob('*.md')))


# Singleton instance
changelog_writer = ChangelogWriter()
