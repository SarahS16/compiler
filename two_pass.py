import re

class TwoPassCompiler:
    def __init__(self):
        self.instructions = []  # Stores intermediate instructions
        self.in_if_block = False  # Flag to track if inside an if block
        self.code_lines = []  # Stores the final lines of Python code
        self.indentation_level = 0  # Tracks the level of indentation (e.g., inside an if block)
        self.if_conditions = []  # Stores the conditions for the if statement
        self.if_actions = []  # Stores actions inside the if statement
        self.keywords = {'if', 'else', 'while'}  #Python keywords

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
                #self.instructions.append((value.upper(), value))
                self.instructions.append(('KEYWORD', value))
            else:
                self.instructions.append((kind, value))
        print("Token Stream: ", self.instructions)




    # Second pass: Generate Python code from the intermediate instructions
    def second_pass(self):
        assembly_instructions = []
        register_counter = 0
        label_counter = 0
        token_stack = []
        current_keyword = None
        current_lhs = None  # To track variable assignment
        rhs_stack = []      # To process RHS expressions

        def allocate_register():
            nonlocal register_counter
            reg = f"R{register_counter}"
            register_counter += 1
            return reg

        def generate_label():
            nonlocal label_counter
            label = f"L{label_counter}"
            label_counter += 1
            return label

        def handle_if(tokens):
            print(tokens)
            tokens.reverse()  # Reverse to process right-to-left
            lhs, operator, rhs = None, None, None

            while tokens:
                token_kind, token_value = tokens.pop()
                if token_kind == 'ID' or token_kind == 'NUMBER':
                    reg = allocate_register()
                    if token_kind == 'ID':
                        assembly_instructions.append(f"LOAD {reg}, {token_value}")
                    else:
                        assembly_instructions.append(f"LOAD {reg}, #{token_value}")

                    if lhs is None:
                        lhs = reg
                    else:
                        rhs = reg
                elif token_kind in ['GT', 'LT', 'EQ']:
                    # operator = token_value
                    operator = token_kind
                elif token_kind in ['LPAREN', 'RPAREN']:
                    continue
                else:
                    raise ValueError(f"Unexpected token in 'if' condition: {token_kind}")

            if not (lhs and operator and rhs):
                raise ValueError("Incomplete condition in 'if' statement.")

            op_map = {'GT': 'CMP_GT', 'LT': 'CMP_LT', 'EQ': 'CMP_EQ'}
            assembly_operator = op_map.get(operator)
            if not assembly_operator:
                raise ValueError(f"Unsupported operator in 'if': {operator}")

            end_label = generate_label()
            assembly_instructions.append(f"{assembly_operator} {lhs}, {rhs}")
            assembly_instructions.append(f"JUMP_IF_FALSE {end_label}")
            return end_label

        # Define keyword handlers
        keyword_handlers = {
            'if': handle_if,
        }

        def process_rhs():
            """Process the RHS stack into assembly instructions."""
            while len(rhs_stack) > 1:
                operand1 = rhs_stack.pop(0)
                operator = rhs_stack.pop(0)
                operand2 = rhs_stack.pop(0)

                op_map = {'PLUS': 'ADD', 'MINUS': 'SUB', 'MUL': 'MUL', 'DIV': 'DIV'}
                if operator not in op_map:
                    raise ValueError(f"Invalid operator: {operator}")

                assembly_operator = op_map[operator]
                temp_reg = allocate_register()
                assembly_instructions.append(f"{assembly_operator} {operand1}, {operand2}")
                rhs_stack.insert(0, temp_reg)  # Push result back as operand

            if rhs_stack:
                return rhs_stack.pop(0)
            return None

        # Main loop to process instructions
        for kind, value in self.instructions:
            print(f"kind: {kind} value: {value}")
            # if kind in keyword_handlers:
            #     # Process the previous keyword if a new one starts
            #     if current_keyword:
            #         keyword_handlers[current_keyword](token_stack)
            #         token_stack = []

            #     current_keyword = kind  # Start handling the new keyword
            if kind == 'KEYWORD':
                if value in keyword_handlers:
                    if current_keyword:
                        keyword_handlers[current_keyword](token_stack)
                        token_stack = []
                    current_keyword = value
            elif kind == 'NEWLINE':
                if current_keyword:
                    keyword_handlers[current_keyword](token_stack)
                    current_keyword = None
                    token_stack = []
                elif current_lhs:
                    # Finalize variable assignment
                    final_value = process_rhs()
                    if final_value:
                        assembly_instructions.append(f"STORE {current_lhs}, {final_value}")
                    current_lhs = None
            elif current_keyword:
                # Collect tokens for the current keyword
                token_stack.append((kind, value))
            else:
                # Handle non-keyword instructions
                if kind == 'ID':  # Variable names
                    if current_lhs is None:
                        current_lhs = value  # Assign LHS
                    else:
                        rhs_stack.append(value)  # Add to RHS stack
                elif kind == 'ASSIGN':  # Assignment operator
                    assembly_instructions.append(f"; Assigning value to {current_lhs}")
                elif kind == 'NUMBER':  # Numbers
                    reg = allocate_register()
                    assembly_instructions.append(f"LOAD {reg}, #{value}")
                    rhs_stack.append(reg)
                elif kind in ['PLUS', 'MINUS', 'MUL', 'DIV']:  # Operators
                    rhs_stack.append(kind)

        # Handle any remaining keyword or variable assignment
        if current_keyword:
            keyword_handlers[current_keyword](token_stack)
        elif current_lhs:
            final_value = process_rhs()
            if final_value:
                assembly_instructions.append(f"STORE {current_lhs}, {final_value}")

        return "\n".join(assembly_instructions)













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
    # code = """ 
    #     x = 9
    #     y = x + 9
    #     """
    # code2 = """
    #     x = 9
    #     if (x > 7)
    # """
    code3 = """ x = 10 + 7 """

    
    compiler = TwoPassCompiler()
    compiled_code = compiler.compile(code3)

