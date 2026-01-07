"""
Formatter Module

Handles string unescaping and content formatting for changelog output.
Converts JSON-escaped strings to proper markdown-ready text.
"""

import re


class Formatter:
    """
    Formats extracted content for markdown output.
    
    Unescaping order is important:
    1. \\\\n -> \\n (quad backslash to double)
    2. \\n -> newline (double backslash n to actual newline)
    3. \\r -> (remove carriage returns)
    4. \\\\" -> \\" (quad to double)
    5. \\" -> " (escaped quotes to actual quotes)
    6. \\t -> tab
    7. \\\\ -> \\ (remaining double backslashes)
    """
    
    def unescape_content(self, text: str) -> str:
        """
        Unescape JSON-encoded string content to readable text.
        
        Args:
            text: JSON-escaped string content
            
        Returns:
            Properly formatted text with real newlines and quotes
        """
        if not text:
            return text
        
        result = text
        
        # Step 1: Handle quadruple-escaped newlines first (\\\\n -> actual newline)
        result = result.replace('\\\\n', '\n')
        
        # Step 2: Handle double-escaped newlines (\\n -> actual newline)
        result = result.replace('\\n', '\n')
        
        # Step 3: Remove carriage returns
        result = result.replace('\\r', '')
        result = result.replace('\r', '')
        
        # Step 4: Handle quadruple-escaped quotes (\\\\" -> ")
        result = result.replace('\\\\"', '"')
        
        # Step 5: Handle double-escaped quotes (\\" -> ")
        result = result.replace('\\"', '"')
        
        # Step 6: Handle escaped tabs
        result = result.replace('\\t', '\t')
        
        # Step 7: Handle remaining double backslashes
        result = result.replace('\\\\', '\\')
        
        # Clean up any multiple consecutive blank lines (max 2)
        result = re.sub(r'\n{4,}', '\n\n\n', result)
        
        return result.strip()
    
    def adjust_header_levels(self, text: str, min_level: int = 3) -> str:
        """
        Adjust markdown header levels to ensure logical flow.
        
        All headers in the content will be bumped to at least min_level
        (default ### for content under ## sections).
        
        For example:
        - # Header becomes ### Header
        - ## Header becomes ### Header
        - ### Header stays ### Header
        - #### Header stays #### Header
        
        Args:
            text: Markdown content that may contain headers
            min_level: Minimum header level (number of #)
            
        Returns:
            Text with adjusted header levels
        """
        if not text:
            return text
        
        lines = text.split('\n')
        adjusted_lines = []
        
        for line in lines:
            # Check if line starts with markdown header
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                current_hashes = match.group(1)
                header_text = match.group(2)
                current_level = len(current_hashes)
                
                # If current level is less than minimum, bump it up
                if current_level < min_level:
                    new_hashes = '#' * min_level
                    line = f"{new_hashes} {header_text}"
            
            adjusted_lines.append(line)
        
        return '\n'.join(adjusted_lines)
    
    def format_changelog_content(
        self, 
        subtask_id: str, 
        mode: str, 
        instruction: str, 
        result: str,
        timestamp: str
    ) -> str:
        """
        Format a complete changelog entry as markdown.
        
        Args:
            subtask_id: The unique subtask identifier
            mode: The mode (ask, code, debug, architect)
            instruction: Raw instruction content
            result: Raw result content
            timestamp: ISO format timestamp
            
        Returns:
            Formatted markdown string
        """
        # Unescape content
        clean_instruction = self.unescape_content(instruction)
        clean_result = self.unescape_content(result)
        
        # Adjust header levels in instruction and result content
        # Headers inside ## sections should be at least ### (level 3)
        adjusted_instruction = self.adjust_header_levels(clean_instruction, min_level=3)
        adjusted_result = self.adjust_header_levels(clean_result, min_level=3)
        
        # Build markdown content with proper header hierarchy
        # # Part of Changelog (top level)
        # ## Task ID (level 2)
        # ## Instruction (level 2)
        # ## Result (level 2)
        # Content headers inside are ### or deeper
        markdown = f"""# Part of Changelog

## Task ID: {subtask_id}

**Mode:** {mode}
**Completed:** {timestamp}

---

## Instruction

{adjusted_instruction}

---

## Result

{adjusted_result}
"""
        
        return markdown
    
    def sanitize_filename(self, text: str) -> str:
        """
        Sanitize a string for use in a filename.
        
        Args:
            text: String to sanitize
            
        Returns:
            Filename-safe string
        """
        # Replace unsafe characters
        unsafe_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        result = text
        for char in unsafe_chars:
            result = result.replace(char, '-')
        
        return result


# Singleton instance
formatter = Formatter()
