# Roo Code Changelogger - Architecture Plan

**Created:** 2026-01-07
**Language:** Python 3.x
**Purpose:** Automatically extract and log completed subtask instructions and results from Roo Code's Orchestrator mode.

---

## Overview

This tool monitors Roo Code's conversation history files for completed subtasks, extracts both the instruction and result, and saves them as timestamped markdown changelog files.

### Key Features

1. **Real-time monitoring** - Uses file system watchers (not polling) to detect changes instantly without SSD wear
2. **Smart file reading** - Only reads NEW bytes added to files, not entire files
3. **Deduplication** - Tracks processed subtask IDs to prevent duplicate entries
4. **Log rotation** - Automatically rotates processed ID logs (3 files, 1MB each)
5. **Graceful handling** - Skips entries with missing instruction or result patterns

---

## Data Flow

```
Roo Code Tasks Folder
         │
         ▼
┌─────────────────────┐
│  File System Watch  │  (watchdog library)
│  (event-driven)     │
└─────────────────────┘
         │
         ▼ file change event
┌─────────────────────┐
│  Debounce (500ms)   │  Wait for file write to complete
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Incremental Read   │  Only read bytes added since last read
│  (max 5MB cap)      │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Pattern Parser     │  Find "Subtask X completed" patterns
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Deduplication      │  Check if ID already processed
└─────────────────────┘
         │
         ▼ (new ID only)
┌─────────────────────┐
│  Extract Content    │  Get instruction + result
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Format & Unescape  │  \\n → newline, \\" → "
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Write Changelog    │  Save timestamped .md file
└─────────────────────┘
```

---

## Pattern Specifications

### Subtask Result Pattern

**Start marker:**
```
"content":"Subtask [UUID] completed.\n\nResult:\n
```

**End marker:**
```
"},{"type":"text","text":"<environment_details>
```

**Example:**
```json
"content":"Subtask 09d0cb0e-5c00-4df2-90cf-f52c4f85bcfc completed.\n\nResult:\nThe task was completed successfully...[content]..."},{"type":"text","text":"<environment_details>
```

### Subtask Instruction Pattern

**Start markers (look for NEAREST one BEFORE the result):**
```
"name":"new_task","input":{"mode":"ask","message":"
"name":"new_task","input":{"mode":"code","message":"
"name":"new_task","input":{"mode":"debug","message":"
"name":"new_task","input":{"mode":"architect","message":"
```

**End marker:**
```
","todos":"
```

**Example:**
```json
"name":"new_task","input":{"mode":"code","message":"Please implement the feature...[instruction]...","todos":"
```

---

## String Unescaping Rules

Applied in order:

1. `\\n` → newline (double-escaped newlines first)
2. `\n` → newline (single-escaped newlines second)
3. `\\"` → `"` (escaped quotes)

---

## Configuration (.env)

```env
# Source: Where Roo Code stores conversation history
ROO_TASKS_PATH=C:\Users\carl\AppData\Roaming\Code\User\globalStorage\rooveterinaryinc.roo-cline\tasks

# Output: Where changelogs are saved (full path, flat folder)
CHANGELOG_OUTPUT_PATH=C:\changelogger\changelogs

# Logs: Where processed IDs are tracked (full path)
PROCESSED_IDS_LOG_PATH=C:\changelogger\logs

# Performance tuning
MAX_READ_BYTES=5242880           # 5 MB max per file read
DEBOUNCE_SECONDS=0.5             # Wait time after file change before reading
MAX_LOG_FILE_SIZE_BYTES=1048576  # 1 MB per log file
LOG_ROTATION_COUNT=3             # Keep 3 rotated log files
```

---

## Output Format

### Filename Format
```
{ISO_TIMESTAMP}_{SUBTASK_ID_SHORT}.md
```

Example: `2026-01-07T11-15-30-123Z_09d0cb0e.md`

### File Content Format
```markdown
# Subtask: 09d0cb0e-5c00-4df2-90cf-f52c4f85bcfc

**Mode:** code
**Completed:** 2026-01-07T11:15:30.123Z

---

## Instruction

[The extracted instruction content with newlines properly rendered]

---

## Result

[The extracted result content with newlines properly rendered]
```

---

## Project Structure

```
c:/changelogger/
├── .env                          # Configuration
├── .gitignore                    # Ignore logs, __pycache__, etc.
├── requirements.txt              # Python dependencies
├── README.md                     # Usage documentation
├── src/
│   ├── __init__.py
│   ├── main.py                   # Entry point
│   ├── watcher.py                # File system watcher (watchdog)
│   ├── parser.py                 # Pattern matching & extraction
│   ├── file_tracker.py           # Incremental file position tracking
│   ├── deduplication.py          # ID tracking & log rotation
│   ├── formatter.py              # String unescaping
│   └── writer.py                 # Safe file writing
├── changelogs/                   # Output directory (flat)
└── logs/                         # Processed ID logs
    ├── processed_ids.log
    ├── processed_ids.log.1
    └── processed_ids.log.2
```

---

## Dependencies

```
# requirements.txt
watchdog>=3.0.0       # Cross-platform file system events
python-dotenv>=1.0.0  # Environment variable loading
```

Both are pure Python with no native compilation requirements.

---

## Smart File Reading Strategy

### Problem
- JSON files grow very large (250KB for ONE subtask)
- Active sessions can produce 10-50MB files
- Reading entire file on every change is wasteful

### Solution: Incremental Position Tracking

```python
file_positions = {}  # {filepath: last_byte_position}

def on_file_change(filepath):
    current_size = os.path.getsize(filepath)
    
    # On first encounter after script start, set baseline to current size
    # This ensures we only process NEW content
    if filepath not in file_positions:
        file_positions[filepath] = current_size
        return  # Skip - this is startup baseline
    
    last_position = file_positions[filepath]
    
    if current_size <= last_position:
        return  # File truncated or no new data
    
    # Cap read size for safety
    bytes_to_read = min(current_size - last_position, MAX_READ_BYTES)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        f.seek(last_position)
        new_content = f.read(bytes_to_read)
    
    process_content(new_content, filepath)
    file_positions[filepath] = current_size
```

### Why 5MB Cap is Safe
- Reading 5MB from SSD: ~10-20ms
- Single subtask rarely exceeds 500KB
- 5MB allows ~10 simultaneous subtask completions
- Provides safety net against runaway reads

---

## Startup Behavior

On script start:
1. Scan all `api_conversation_history.json` files in tasks folder
2. Record current file sizes as baseline positions
3. Do NOT process any existing content
4. Only process NEW content added after startup

This ensures no historical data is accidentally logged.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Missing result end pattern | Skip this entry, log warning |
| Missing instruction pattern | Skip this entry, log warning |
| Duplicate subtask ID | Skip (already in processed log) |
| File read error | Log error, continue watching |
| Write permission error | Log error, retry on next change |
| Malformed JSON content | Skip entry, continue processing |

---

## Log Rotation

When `processed_ids.log` exceeds 1MB:
1. Delete `processed_ids.log.3` if exists
2. Rename `.log.2` → `.log.3`
3. Rename `.log.1` → `.log.2`
4. Rename `.log` → `.log.1`
5. Create new empty `.log`

This maintains a rolling window of ~3MB of processed IDs.

---

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Configure paths in .env file
# Edit .env with your paths

# Run the watcher
python src/main.py
```

The script will run continuously, watching for new subtask completions.

---

## Implementation Phases

1. **Phase 1:** Project setup (requirements.txt, .env, .gitignore)
2. **Phase 2:** File tracker module (incremental position tracking)
3. **Phase 3:** Parser module (pattern extraction)
4. **Phase 4:** Deduplication module (ID tracking + log rotation)
5. **Phase 5:** Formatter module (string unescaping)
6. **Phase 6:** Writer module (safe changelog file writing)
7. **Phase 7:** Watcher module (watchdog integration)
8. **Phase 8:** Main orchestrator (tying it all together)
9. **Phase 9:** Testing with real Roo Code files
10. **Phase 10:** Documentation (README.md)
