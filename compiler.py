from manager import Manager
from var import Var
from error import error
from lexer import Reader
import config

class Compiler:
    manager: Manager
    type_names = ["num", "none", "array"]
    type_to_width = {
        "num": 1,
        "none": 1,
        "array": -1
    }
    vars: dict[str, Var] = {}

    def __init__(self):
        self.manager = Manager(self.vars)

    def get_var_names(self) -> list[str]:
        return [x for x in self.vars]
        
    def declare(self, expr: list[str]):
        type = expr[0]
        name = expr[1]
        
        if type == "array":
            error("arrays aren't implemented yet")
        else: # anything else (num, none, MyObject, ...)
            self.manager.get_var(name, type, self.type_to_width[type], not config.num_reg)

        if len(expr) >= 3:
            self.compile_expr(expr[1:]) # num x = 3 -> num x; x = 3

    def compile_expr(self, expr: list[str]):
        assert len(expr) >= 2

        if expr[1] == "=": # set to already existing variable
            if expr[0] not in self.vars:
                error(f"undefined variable {expr[0]}")

            self.manager.evaluate(self.manager.make_tokens(expr[2:], [], self.get_var_names()), self.vars, self.vars[expr[0]])

        elif expr[0] in self.type_names: # declaring
            self.declare(expr) # forward

        elif expr[0] == "return":
            self.manager.evaluate(self.manager.make_tokens(expr[1:]), self.vars, ret = True)

        # todo miscs like in, out, pop?, push?, halt,
        #? ^ handle when calling functions.

    def compile(self, exprs: Reader[list[str]]):
        def is_expr(expr: list[str]):
            if len(expr) >= 2:
                if (expr[0] == "return") or (expr[1] == "=" and len(expr >= 3)) or (expr[0] in self.type_names): return True
                    
            return False

        while not exprs.finished():
            expr = exprs.read()

            if len(expr) == 0: continue

            if is_expr(expr):
                self.compile_expr(expr)
            elif expr[0] == "function":
                #self.compile_func(self, expr)
                error("functions arent implemented yet")
            elif expr[0] == "object":
                error("objects arent implemented yet")
            elif expr[0] == "if":
                error("conditionals arent implemented yet")
