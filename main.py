from sys      import argv as args
from compiler import Compiler
from parse    import Parser
from lexer    import Lexer
from rich     import print
from os       import path
import config
import error

print("Tukpiler 2 2021\n")

#* input
file  = "input.tuk"
out   = f"output.{config.arch}"
DEBUG = False
not_found = ""

if len(args) >= 3:
    # command line mode

    def get_operand() -> str:
        operand = args[i + 2]
        return operand

    def is_key(x: str, y: str) -> bool:
        if x == f"--{y}" or f"-{y[0]}":
            return True
        return False

    i = 0
    a = 0
    while i < len(args) - 1:
        arg = args[i + 1]

        if arg[0] == "-" or (arg[0] == arg[1] == "-"):
            key = arg

            if is_key(key, "debug"):
                DEBUG = True
            elif is_key(key, "input"):
                file = get_operand(); i += 1
            elif is_key(key, "output"):
                file = get_operand(); i += 1
        else:
            if a == 0: # source
                file = arg
            elif a == 1: # output
                out = arg

            a += 1
        i += 1

    not_found = f"{file} is not a file! check again that its in the same directory as from where youre running from"
else:
    file  = ""
    out   = ""

    # manual mode
    if file == "":
        file = input("file to compile: ")
    if out == "":
        out = input("where to store the result?: ")

    not_found = "{file} isnt a file! check again that its in the same directory as main.py"
    
if not path.isfile(file):
    print(not_found)

code = open(file, "r").readlines()
config.debug = DEBUG

#* lexer
separators = ["+", "-", "/", "//", "*", "%", "^", "&", "|", "=", "==", ">=", "<=", "!=", ">", "<", "->", "{", "}", ",", "(", ")", ";", "[", "]", " "]
lexer = Lexer(
    separators, # separators
    [] #? style
) # rest is default

tokens = lexer.lex(code)

#* parser
parser = Parser(tokens)
exprs = parser.parse()
print(exprs)

#* compiler
compiler = Compiler(parser)
compiler.compile(exprs)

#* output
compiler.output(out)

if len(error.errors) > 0:
    print(f"[red]Compiled unsuccesfully with {len(error.errors)} error(s)")
else:
    print(f"[green]Compiled succesfully with 0 errors and saved in {out}")