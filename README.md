# Roovision 🔭

**Automated changelog extraction for Roo Code's Orchestrator mode**

Roovision monitors Roo Code VS Extension's conversation history files and automatically extracts completed subtask instructions and results into timestamped markdown changelog files.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Features

- 🔍 **Real-time monitoring** - Uses file system watchers (not polling) for instant detection without SSD wear
- 📖 **Smart file reading** - Only reads NEW bytes with overlap buffer, handles large files efficiently
- 🔄 **Deduplication** - Tracks processed subtask IDs to prevent duplicate entries
- 📁 **Log rotation** - Automatically rotates processed ID logs (3 files × 1MB each)
- 📚 **Multiple subtask support** - Handles multiple completions in a single file update
- 🆕 **New conversation tracking** - Automatically tracks new Roo Code conversations created while running
- ⏰ **File age filter** - Only track recent files to reduce startup time
- 🔇 **Ask-mode filtering** - Optionally skip ask-mode subtasks (no code changes)
- 🌍 **UTC timestamps** - All timestamps use UTC for consistent global ordering
- ⚡ **Graceful error handling** - Skips incomplete patterns, continues on errors

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/roovision.git
cd roovision
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure
```bash
# Copy the example config
cp .env.example .env

# Edit .env with your paths (see Configuration section below)
```

### 4. Run
```bash
python src/main.py
```

## Configuration

Copy `.env.example` to `.env` and customize:

```env
# Source: Where Roo Code stores conversation history
# Adjust YOUR_USERNAME to match your Windows user
ROO_TASKS_PATH=C:\Users\YOUR_USERNAME\AppData\Roaming\Code\User\globalStorage\rooveterinaryinc.roo-cline\tasks

# Output: Where changelogs are saved
CHANGELOG_OUTPUT_PATH=C:\path\to\roovision\changelogs

# Logs: Where processed IDs are tracked
PROCESSED_IDS_LOG_PATH=C:\path\to\roovision\logs

# File age filter (only track recent files at startup)
MAX_FILE_AGE_DAYS=7         # 0 = disabled, track all files

# Skip ask-mode subtasks (no code changes made)
SKIP_ASK_MODE=true          # 'true' (default) or 'false'

# Performance tuning
MAX_READ_BYTES=5242880      # 5 MB max per file read
OVERLAP_BYTES=2048          # 2 KB overlap for pattern continuity
DEBOUNCE_SECONDS=0.5        # Wait time after file change

# Log rotation
MAX_LOG_FILE_SIZE_BYTES=1048576  # 1 MB per log file
LOG_ROTATION_COUNT=3             # Keep 3 rotated files
```

## Output

Each completed subtask creates a markdown file:

**Filename format:** `changelog_{UTC_TIMESTAMP}_{SUBTASK_ID}.md`

**Example:** `changelog_2026-01-07T11-30-00-123_UTC_09d0cb0e-5c00-4df2-90cf-f52c4f85bcfc.md`

> **Note:** All timestamps are in UTC for consistent ordering across time zones. Files sorted by name will appear in the order changes actually happened globally.

**Content format:**
```markdown
# Task ID: 09d0cb0e-5c00-4df2-90cf-f52c4f85bcfc

**Mode:** code
**Completed:** 2026-01-07T11:30:00.123 UTC

---

## Instruction

[The instruction given to the subtask]

---

## Result

[The result returned by the subtask]
```

## How It Works

```
Roo Code Tasks Folder
         │
         ▼
┌─────────────────────┐
│  File System Watch  │  (watchdog - event-driven, no polling)
└─────────────────────┘
         │
         ▼ file change event
┌─────────────────────┐
│  Debounce (500ms)   │  Wait for writes to complete  
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Incremental Read   │  Only read new bytes + overlap
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Pattern Parser     │  Find ALL complete subtasks
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Deduplication      │  Skip already processed IDs
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Write Changelog    │  One .md file per subtask
└─────────────────────┘
```

## Project Structure

```
roovision/
├── .env.example              # Example configuration (copy to .env)
├── .gitignore
├── LICENSE                   # MIT License
├── README.md
├── requirements.txt
├── plans/
│   └── architecture.md       # Detailed architecture docs
└── src/
    ├── __init__.py
    ├── main.py               # Entry point
    ├── config.py             # Configuration loader
    ├── watcher.py            # File system watcher
    ├── file_tracker.py       # Incremental position tracking
    ├── parser.py             # Pattern extraction
    ├── deduplication.py      # ID tracking & log rotation
    ├── formatter.py          # String unescaping
    └── writer.py             # Changelog file writing
```

## Requirements

- Python 3.8+
- Dependencies:
  - `watchdog` - Cross-platform file system events
  - `python-dotenv` - Environment variable loading

## Startup Behavior

On script start:
1. Records current file sizes as baseline
2. Does NOT process any existing content
3. Only processes NEW content added after startup

This ensures no historical data is accidentally logged.

## Troubleshooting

**No changelogs appearing?**
- Check that Roo Code's Orchestrator mode is completing subtasks
- Verify the `ROO_TASKS_PATH` in `.env` is correct
- Look for error messages in the console output

**Too many files being tracked?**
- Reduce `MAX_FILE_AGE_DAYS` to only track recent conversations

**Duplicate entries?**
- The deduplication system should prevent this
- Check `logs/processed_ids.log` for tracked IDs

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built to work with [Roo Code](https://marketplace.visualstudio.com/items?itemName=RooVeterinaryInc.roo-cline) VS Code extension.
