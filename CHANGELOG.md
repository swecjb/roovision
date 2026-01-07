# Changelog

All notable changes to Roovision will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-01-07

### Changed

- **Markdown header hierarchy** - Improved structure for better document organization:
  - Added `# Part of Changelog` as top-level header in each file
  - Changed `# Task ID:` to `## Task ID:` (level 2)
  - Kept `## Instruction` and `## Result` at level 2
  - Content headers inside instructions/results are auto-adjusted to `###` or deeper to maintain logical flow

### Technical

- Added `adjust_header_levels()` function in formatter to process embedded headers
- Headers in extracted content are bumped to minimum level 3 to nest properly under the `## Instruction` and `## Result` sections

---

## [1.0.0] - 2026-01-07

### Initial Release 🎉

Roovision is an automated changelog extraction tool for Roo Code's Orchestrator mode. It monitors conversation history files and automatically extracts completed subtask instructions and results into timestamped markdown changelog files.

### Features

- **Real-time monitoring** - Uses file system watchers (watchdog) for instant detection without SSD wear
- **Smart incremental file reading** - Only reads NEW bytes with overlap buffer, handles large files efficiently
- **Pattern parsing** - Extracts subtask instructions and results using regex pattern matching
- **Deduplication** - Tracks processed subtask IDs to prevent duplicate entries
- **Log rotation** - Automatically rotates processed ID logs (3 files × 1MB each)
- **Multiple subtask support** - Handles multiple completions in a single file update
- **New conversation tracking** - Automatically tracks new Roo Code conversations created while running
- **File age filter** - Only track recent files (configurable, default 7 days) to reduce startup time
- **Ask-mode filtering** - Optionally skip ask-mode subtasks (no code changes)
- **UTC timestamps** - All timestamps use UTC for consistent global ordering
- **Graceful error handling** - Skips incomplete patterns, continues on errors
- **Atomic file writing** - Prevents corruption during changelog creation
- **Configurable via environment variables** - Easy setup through `.env` file

### Configuration Options

- `ROO_TASKS_PATH` - Path to Roo Code's conversation history
- `CHANGELOG_OUTPUT_PATH` - Where changelogs are saved
- `PROCESSED_IDS_LOG_PATH` - Where processed IDs are tracked
- `MAX_FILE_AGE_DAYS` - File age filter (0 = disabled)
- `SKIP_ASK_MODE` - Skip ask-mode subtasks (default: true)
- `MAX_READ_BYTES` - Maximum bytes per file read
- `OVERLAP_BYTES` - Overlap for pattern continuity
- `DEBOUNCE_SECONDS` - Wait time after file change
- `MAX_LOG_FILE_SIZE_BYTES` - Size per log file
- `LOG_ROTATION_COUNT` - Number of rotated log files

### Output Format

Changelogs are saved as: `changelog_{UTC_TIMESTAMP}_{SUBTASK_ID}.md`

Each file contains:
- Task ID
- Mode (code, debug, architect, ask)
- Completion timestamp (UTC)
- Original instruction
- Subtask result

[1.0.1]: https://github.com/swecjb/roovision/releases/tag/v1.0.1
[1.0.0]: https://github.com/swecjb/roovision/releases/tag/v1.0.0
