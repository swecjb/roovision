"""
Parser Module

Extracts subtask instructions and results from conversation history content.
Finds ALL complete patterns in a single read operation.
Only processes patterns that are fully complete (have both start AND end markers).
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class SubtaskEntry:
    """Represents an extracted subtask with instruction and result."""
    subtask_id: str
    mode: str  # ask, code, debug, architect
    instruction: str
    result: str
    # Position in content where the result END marker was found
    # (used to determine if this is "new" content)
    result_end_position: int


class Parser:
    """
    Parses conversation history JSON content to extract subtask entries.
    
    Pattern structure:
    - Result: "content":"Subtask [ID] completed.\\n\\nResult:\\n[CONTENT]"},{"type":"text","text":"<environment_details>
    - Instruction: "name":"new_task","input":{"mode":"[MODE]","message":"[CONTENT]","todos":"
    """
    
    # Pattern to find subtask completion results
    RESULT_START_PATTERN = re.compile(
        r'"content":"Subtask ([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}) completed\.\\n\\nResult:\\n'
    )
    
    # End marker for results
    RESULT_END_MARKER = '"},{"type":"text","text":"<environment_details>'
    
    # Patterns to find instruction starts (for different modes)
    INSTRUCTION_PATTERNS = [
        ('"name":"new_task","input":{"mode":"ask","message":"', 'ask'),
        ('"name":"new_task","input":{"mode":"code","message":"', 'code'),
        ('"name":"new_task","input":{"mode":"debug","message":"', 'debug'),
        ('"name":"new_task","input":{"mode":"architect","message":"', 'architect'),
    ]
    
    # End marker for instructions
    INSTRUCTION_END_MARKER = '","todos":"'
    
    def find_all_complete_subtasks(
        self,
        content: str,
        read_start: int,
        last_position: int,
        filepath: str = None
    ) -> List[SubtaskEntry]:
        """
        Find all complete subtask entries in the content.
        
        Args:
            content: The string content read from file
            read_start: Absolute file position where this read started
            last_position: Position we had before read (to determine "new" patterns)
            filepath: Path to the file (for reading more content if needed)
        
        Returns:
            List of SubtaskEntry objects for all NEW complete subtasks found
        """
        entries = []
        
        # Debug: Show what we're searching
        print(f"[PARSER] Searching {len(content)} bytes (read_start={read_start}, last_position={last_position})")
        
        # Find all result start patterns
        all_matches = list(self.RESULT_START_PATTERN.finditer(content))
        print(f"[PARSER] Found {len(all_matches)} result pattern matches")
        
        for match in all_matches:
            subtask_id = match.group(1)
            result_content_start = match.end()
            print(f"[PARSER]   Examining subtask {subtask_id} at content offset {match.start()}")
            
            # Find the end marker AFTER this result start
            result_end_pos = content.find(self.RESULT_END_MARKER, result_content_start)
            
            if result_end_pos == -1:
                # Result not complete yet (no end marker)
                print(f"[PARSER]   -> No end marker found, skipping")
                continue
            
            # Calculate absolute position of the end marker in the file
            absolute_end_position = read_start + result_end_pos
            print(f"[PARSER]   -> End marker at content offset {result_end_pos}, absolute pos {absolute_end_position}")
            
            # Extract result content
            result_content = content[result_content_start:result_end_pos]
            
            # Find the NEAREST instruction BEFORE this result
            # First try in the current content buffer
            instruction_data = self._find_nearest_instruction(content, match.start())
            
            if instruction_data is None and filepath:
                # Instruction not in current buffer - need to read more of the file
                print(f"[PARSER]   -> Instruction not in buffer, reading full file for {subtask_id}")
                instruction_data = self._find_instruction_in_file(
                    filepath, 
                    read_start + match.start()  # absolute position of result
                )
            
            if instruction_data is None:
                print(f"[PARSER] Warning: Found result for {subtask_id} but no instruction. Skipping.")
                continue
            
            instruction_content, mode = instruction_data
            
            entries.append(SubtaskEntry(
                subtask_id=subtask_id,
                mode=mode,
                instruction=instruction_content,
                result=result_content,
                result_end_position=absolute_end_position
            ))
            
            print(f"[PARSER] Found complete subtask: {subtask_id} (mode: {mode})")
        
        return entries
    
    def _find_instruction_in_file(
        self,
        filepath: str,
        result_absolute_position: int
    ) -> Optional[Tuple[str, str]]:
        """
        Read the file and find the nearest instruction before the result position.
        
        Args:
            filepath: Path to the conversation history file
            result_absolute_position: Absolute file position of the result start
        
        Returns:
            Tuple of (instruction_content, mode) or None if not found
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Read everything up to the result position
                content_before_result = f.read(result_absolute_position)
            
            # Find the nearest instruction in this content
            return self._find_nearest_instruction(content_before_result, len(content_before_result))
            
        except Exception as e:
            print(f"[PARSER] Error reading file for instruction: {e}")
            return None
    
    def _find_nearest_instruction(
        self, 
        content: str, 
        before_position: int
    ) -> Optional[Tuple[str, str]]:
        """
        Find the nearest instruction pattern BEFORE the given position.
        
        Args:
            content: Full content string
            before_position: Position to search before
        
        Returns:
            Tuple of (instruction_content, mode) or None if not found
        """
        best_match = None
        best_position = -1
        best_mode = None
        
        # Search for each instruction pattern type
        for pattern_str, mode in self.INSTRUCTION_PATTERNS:
            # Find all occurrences of this pattern
            search_start = 0
            while True:
                pos = content.find(pattern_str, search_start)
                if pos == -1 or pos >= before_position:
                    break
                
                # This occurrence is before our target and closer than previous best
                if pos > best_position:
                    best_position = pos
                    best_match = pattern_str
                    best_mode = mode
                
                search_start = pos + 1
        
        if best_match is None:
            return None
        
        # Extract the instruction content
        instruction_start = best_position + len(best_match)
        
        # Find the end marker
        instruction_end = content.find(self.INSTRUCTION_END_MARKER, instruction_start)
        
        if instruction_end == -1 or instruction_end > before_position:
            # Instruction end marker not found or after the result (malformed)
            return None
        
        instruction_content = content[instruction_start:instruction_end]
        
        return (instruction_content, best_mode)


# Singleton instance
parser = Parser()
