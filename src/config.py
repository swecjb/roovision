"""
Configuration loader for Roovision.
Loads settings from .env file and provides defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class Config:
    """Configuration settings loaded from environment variables."""
    
    # Source path - where Roo Code stores conversation history
    ROO_TASKS_PATH: str = os.getenv(
        'ROO_TASKS_PATH',
        r'C:\Users\carl\AppData\Roaming\Code\User\globalStorage\rooveterinaryinc.roo-cline\tasks'
    )
    
    # Output path - where changelogs are saved
    CHANGELOG_OUTPUT_PATH: str = os.getenv(
        'CHANGELOG_OUTPUT_PATH',
        r'C:\changelogger\changelogs'
    )
    
    # Log path - where processed IDs are tracked
    PROCESSED_IDS_LOG_PATH: str = os.getenv(
        'PROCESSED_IDS_LOG_PATH',
        r'C:\changelogger\logs'
    )
    
    # Performance tuning
    MAX_READ_BYTES: int = int(os.getenv('MAX_READ_BYTES', 5242880))  # 5 MB
    OVERLAP_BYTES: int = int(os.getenv('OVERLAP_BYTES', 2048))  # 2 KB
    DEBOUNCE_SECONDS: float = float(os.getenv('DEBOUNCE_SECONDS', 0.5))
    
    # File age filter (0 = disabled, track all files)
    MAX_FILE_AGE_DAYS: int = int(os.getenv('MAX_FILE_AGE_DAYS', 7))
    
    # Log rotation
    MAX_LOG_FILE_SIZE_BYTES: int = int(os.getenv('MAX_LOG_FILE_SIZE_BYTES', 1048576))  # 1 MB
    LOG_ROTATION_COUNT: int = int(os.getenv('LOG_ROTATION_COUNT', 3))
    
    # Skip ask mode subtasks (they don't make code changes)
    # Default: true - skip them and don't create changelogs
    SKIP_ASK_MODE: bool = os.getenv('SKIP_ASK_MODE', 'true').lower() in ('true', '1', 'yes')
    
    # File to watch within each task folder
    CONVERSATION_FILENAME: str = 'api_conversation_history.json'
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Create output directories if they don't exist."""
        Path(cls.CHANGELOG_OUTPUT_PATH).mkdir(parents=True, exist_ok=True)
        Path(cls.PROCESSED_IDS_LOG_PATH).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required paths exist."""
        tasks_path = Path(cls.ROO_TASKS_PATH)
        if not tasks_path.exists():
            print(f"ERROR: ROO_TASKS_PATH does not exist: {cls.ROO_TASKS_PATH}")
            return False
        return True
    
    @classmethod
    def print_config(cls) -> None:
        """Print current configuration for debugging."""
        print("=" * 60)
        print("Roovision Configuration")
        print("=" * 60)
        print(f"ROO_TASKS_PATH:          {cls.ROO_TASKS_PATH}")
        print(f"CHANGELOG_OUTPUT_PATH:   {cls.CHANGELOG_OUTPUT_PATH}")
        print(f"PROCESSED_IDS_LOG_PATH:  {cls.PROCESSED_IDS_LOG_PATH}")
        if cls.MAX_FILE_AGE_DAYS > 0:
            print(f"MAX_FILE_AGE_DAYS:       {cls.MAX_FILE_AGE_DAYS} days (only track recent files)")
        else:
            print(f"MAX_FILE_AGE_DAYS:       0 (disabled - track all files)")
        print(f"MAX_READ_BYTES:          {cls.MAX_READ_BYTES:,} bytes ({cls.MAX_READ_BYTES // 1024 // 1024} MB)")
        print(f"OVERLAP_BYTES:           {cls.OVERLAP_BYTES:,} bytes ({cls.OVERLAP_BYTES // 1024} KB)")
        print(f"DEBOUNCE_SECONDS:        {cls.DEBOUNCE_SECONDS}s")
        print(f"MAX_LOG_FILE_SIZE_BYTES: {cls.MAX_LOG_FILE_SIZE_BYTES:,} bytes ({cls.MAX_LOG_FILE_SIZE_BYTES // 1024 // 1024} MB)")
        print(f"LOG_ROTATION_COUNT:      {cls.LOG_ROTATION_COUNT}")
        print(f"SKIP_ASK_MODE:           {cls.SKIP_ASK_MODE} (skip ask-mode subtasks: {'yes' if cls.SKIP_ASK_MODE else 'no'})")
        print("=" * 60)


# Create singleton instance
config = Config()
