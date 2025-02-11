import antlr4
from SystemVerilogLexer import SystemVerilogLexer
from SystemVerilogParser import SystemVerilogParser
from antlr4.error.ErrorListener import ErrorListener  # Correct import
from uvm_component_function_for_extraction import UVMComponentListener  # Import extraction functions
import os


class MyErrorListener(ErrorListener):  # Custom error listener
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        print(f"Syntax error at line {line}, column {column}: {msg}")
        raise Exception(f"Syntax error at line {line}, column {column}: {msg}")  # Stop parsing on error


def main(filename):
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return

    try:
        with open(filename, 'r') as f:
            data = f.read()
    except IOError as e:
        print(f"Error reading file '{filename}': {e}")
        return

    lexer = SystemVerilogLexer(antlr4.InputStream(data))
    parser = SystemVerilogParser(antlr4.CommonTokenStream(lexer))

    error_listener = MyErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)

    tree = parser.source_text()

    listener = UVMComponentListener(filename)
    walker = antlr4.ParseTreeWalker()
    walker.walk(listener, tree)

    components = listener.get_components()

    if components:
        print("Found components:")
        for component in components:
            print(component)
    else:
        print("No components found.")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        main(filename)
    else:
        print("Please provide a SystemVerilog filename as a command-line argument.")
