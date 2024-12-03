import re

class TwoPassCompiler:
    def __init__(self):
        self.instructions = []  # Stores intermediate instructions
        self.in_if_block = False  # Flag to track if inside an if block
        self.code_lines = []  # Stores the final lines of Python code
        self.indentation_level = 0  # Tracks the level of indentation (e.g., inside an if block)
        self.if_conditions = []  # Stores the conditions for the if statement
        self.if_actions = []  # Stores actions inside the if statement
        self.keywords = {'if', 'else', 'while', 'for', 'def', 'class', 'return'}  # Add Python keywords here

    # First pass: Tokenization and parsing into intermediate representation

    def first_pass(self, code):
        token_specification = [
            ('NUMBER', r'\d+'),                      # Integer number
            ('ASSIGN', r'='),                       # Assignment operator
            ('ID', r'[A-Za-z_][A-Za-z0-9_]*'),      # Identifier
            ('PLUS', r'\+'),                        # Plus sign
            ('MINUS', r'-'),                        # Minus sign
            ('MUL', r'\*'),                         # Multiplication sign
            ('DIV', r'/'),                          # Division sign
            ('LT', r'<'),                           # Less than operator
            ('GT', r'>'),                           # Greater than operator
            ('EQ', r'=='),                          # Equal to operator
            ('GEQ',r'>='),                          # Greater than equal to operator
            ('LPAREN', r'\('),                      # Left Parenthesis
            ('RPAREN', r'\)'),                      # Right Parenthesis
            ('NEWLINE', r'\n'),                     # Newline
            ('SKIP', r'[ \t]+'),                    # Skip spaces and tabs
            ('MISMATCH', r'.'),                     # Any other character
        ]
        tok_regex = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in token_specification)
        line_num = 1
        line_start = 0
        for mo in re.finditer(tok_regex, code):
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'NEWLINE':  # Recognize and append newlines
                self.instructions.append((kind, value))
                line_num += 1
            elif kind == 'SKIP':
                pass
            elif kind == 'MISMATCH':
                raise RuntimeError(f'{value!r} unexpected on line {line_num}')
            elif kind == 'ID' and value in self.keywords:  # Check if the ID is a keyword
                self.instructions.append(('KEYWORD', value))
            else:
                self.instructions.append((kind, value))
        print("Parsed Instructions: ", self.instructions)




    # Second pass: Generate Python code from the intermediate instructions
    def second_pass(self):
        current_assignment = []  # For assignments like x = 9
        condition = []  # For conditions like x < y
        action = []  # For actions inside the if statement

        for kind, value in self.instructions:
            if kind == 'ID':  # Variable names
                if self.in_if_block:
                    condition.append(value)  # Add to condition for the if statement
                elif current_assignment:
                    current_assignment.append(value)  # Add to the assignment
                else:
                    current_assignment = [value]  # Start a new assignment
            elif kind == 'ASSIGN':  # Assignment operator
                current_assignment.append('=')
            elif kind == 'NUMBER':  # Numbers in expressions
                if self.in_if_block:
                    condition.append(value)  # Add to condition if inside an if block
                else:
                    current_assignment.append(value)  # Add to the assignment
            elif kind in ['PLUS', 'MINUS', 'MUL', 'DIV', 'LT', 'GT', 'EQ']:  # Operators
                if self.in_if_block:
                    condition.append(value)  # Add to condition if inside an if block
                else:
                    current_assignment.append(value)  # Add to the assignment
            elif kind == 'IF':  # If condition
                self.in_if_block = True
                self.code_lines.append(self._get_indentation() + "if ", end="")
                self.indentation_level += 1  # Increase indentation level for block
            elif kind == 'LPAREN':  # Left Parenthesis for condition
                if self.in_if_block:
                    condition.append('(')
            elif kind == 'RPAREN':  # Right Parenthesis for condition
                if self.in_if_block:
                    condition.append(')')
            elif kind == 'NEWLINE':  # Newline means we complete an assignment or block
                if current_assignment:
                    self.code_lines.append(self._get_indentation() + "".join(current_assignment))
                    current_assignment = []  # Reset for the next assignment
                elif condition:
                    # Add condition to the if statement
                    self.if_conditions.append("".join(condition))
                    self.code_lines.append(self._get_indentation() + "if " + "".join(condition) + ":")
                    self.in_if_block = False  # End if block
                    condition = []  # Reset condition for the next statement
                    self.indentation_level -= 1  # Decrease indentation level after block
                if action:
                    self.if_actions.append("".join(action))
                    action = []  # Reset the action after it is stored

        # Handle any remaining assignment or condition at the end
        if current_assignment:
            self.code_lines.append(self._get_indentation() + " ".join(current_assignment))
        if condition:
            self.code_lines.append(self._get_indentation() + " ".join(condition))
        
        # Insert dynamic actions inside the if block based on collected conditions
        for action in self.if_actions:
            self.code_lines.append(self._get_indentation() + action)
        
        return "\n".join(self.code_lines)

    def _get_indentation(self):
        return "    " * self.indentation_level  # Generates indentation based on the level

    # Compile the source code using both passes
    def compile(self, code):
        # Perform the first pass: Tokenization and parsing
        self.first_pass(code)
        
        # Perform the second pass: Code generation
        python_code = self.second_pass()
        
        # Print the generated Python code
        print("Generated Python Code:\n", python_code)
        return python_code


# Example usage
if __name__ == '__main__':
    code = "if (x > y) y = 42"
    
    compiler = TwoPassCompiler()
    compiled_code = compiler.compile(code)

