from manager import Manager
from var import Var, Func
from error import error
from lexer import Reader
from parse import Parser
from copy import deepcopy as copy
import config

class Compiler:
    manager: Manager
    type_names = ["num", "none", "array"]
    type_to_width = {
        "num": 1,
        "none": 1,
        "array": -1
    }
    vars : dict[str, Var]  = {}
    funcs: dict[str, Func] = {}

    def __init__(self, parser):
        self.manager = Manager(self.vars, self.funcs, self.type_to_width)
        self.parser: Parser = parser

    def get_var_names(self) -> list[str]:
        return [x for x in self.vars]
        
    def declare(self, expr: list[str]):
        type = expr[0]
        name = expr[1]
        
        if type == "array":
            error("arrays aren't implemented yet")
        else: # anything else (num, none, MyObject, ...)
            references = self.parser.tokens.elements.count(name)
            self.manager.get_var(name, type, self.type_to_width[type])

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
            self.manager.evaluate(self.manager.make_tokens(expr[1:], [], self.get_var_names()), self.vars, ret = True)

        # todo miscs like in, out, pop?, push?, halt,
        #? ^ handle when calling functions.

    def compile_func(self, expr: list[str]):
        # parsing
        name = expr[1]
        args = Reader(expr[3:expr.index(")")]).split(",")
        ret_type = expr[expr.index(")") + 3]

        # setup
        self.funcs[name] = func = Func(name, args, ret_type, self.manager) # woah triple setting :sunglasses:
        vars_save    = copy(self.vars)
        manager_save = copy(self.manager)

        # prepare manager
        self.manager.in_func = True
        #//self.manager.available_reg = list(range(1, config.regs))
        var_names = list(self.vars.keys())
        for var_name in var_names: # remove temps in regs
            var = self.vars[var_name]
            if var.type == "temp" or var.pointer.type in ["reg", "regpoi"]: # its in a register
                var.free()
        self.manager.available_reg.remove(1)

        func.header()

        # compile insides
        self.parser.tokens = Reader(expr[expr.index("{") + 1:expr.index("}")])
        use = self.compile(self.parser.parse())

        # free, finish & clean up
        func.finish(use["reg"])
        self.vars    = vars_save
        self.manager = manager_save

    def compile(self, exprs: Reader[list[str]]) -> dict[str, int]: # returns memory use
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
                self.compile_func(expr)
            elif expr[0] == "if":
                error("conditionals arent implemented yet")
            elif expr[0] == "object":
                error("objects arent implemented yet")

        use = {"reg": 0, "ram": 0}
        use["reg"] = [x for x in range(1, config.regs) if x not in self.manager.available_reg]
        use["ram"] = [x for x in range(1, config.heap) if x not in self.manager.available_ram]

        return use

    def output(self, file_name: str):
        with open(file_name, "w") as f:
            f.write(self.manager.header + self.manager.main)
