from manager import Manager
from var import Var, Func
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
    vars : dict[str, Var]  = {}
    funcs: dict[str, Func] = {}

    def __init__(self, parser):
        self.manager = Manager(self.vars, self.funcs, self.type_to_width)
        self.parser = parser

    def get_var_names(self) -> list[str]:
        return [x for x in self.vars]
        
    def declare(self, expr: list[str]):
        type = expr[0]
        name = expr[1]
        
        if type == "array":
            error("arrays aren't implemented yet")
        else: # anything else (num, none, MyObject, ...)
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
            self.manager.evaluate(self.manager.make_tokens(expr[1:]), self.vars, ret = True)

        # todo miscs like in, out, pop?, push?, halt,
        #? ^ handle when calling functions.

    def compile_func(self, expr: list[str]):
        """
        global funcrcl, func_name, func_ret_addr, vars
        print(f"compiling function {tokens}")
        #function add ( num x , num y ) - > num { ... }

        name = tokens[1]
        func_name = name
        args = parse.split_list(tokens[tokens.index("(") + 1:tokens.index(")")], ",")
        print(args)
        return_type = tokens[tokens.index(")") + 3]

        funcs[name] = Func(name, args, return_type)
        funcrcl.append(f".function_{name}")
        arg_table: dict[str, str] = {}

        # return adress stack fix
        return_address = get_reg()
        funcrcl.append(f"POP {return_address}")
        func_ret_addr = return_address

        # extract arguments' pointers and create/overwrite the variables
        before = copy(vars)
        for arg in args:
            reg = get_reg()
            arg_table[arg[1]] = reg # setup an argument to reg table
            funcrcl.append(f"POP {reg}")
            vars[arg[1]] = Var(arg[1], arg[0], 1, argument = True, reg = reg)    

        # compile insides
        parse.parse(tokens[tokens.index("{") + 1:-1], True)

        if funcrcl[-1][0:3] != "RET": # add return if it doesnt have one
            funcrcl += ["PSH R0", f"PSH {func_ret_addr}", "RET"] # R0 = none

        # free & clean up
        for arg in arg_table: free_reg(arg_table[arg])
        vars = before
        free_reg(return_address)
        """

        name = expr[1]
        args = Reader(expr[3:expr.index(")")]).split(",")
        ret_type = expr[expr.index(")") + 3]

        func = Func(name, args, ret_type)
        self.funcs[name] = func

        self.manager.in_func = True
        func.header()

        # compile insides
        self.parser.tokens = Reader(expr[expr.index("{") + 1:expr.index("}")])
        use = self.compile(self.parser.parse()) # todo implement compiler return use
        use = {"regs": 4, "global_ram": 5}

        # todo add return if doesn't have one (default case)

        # free & clean up
        self.manager.in_func = False

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
                self.compile_func(expr)
            elif expr[0] == "if":
                error("conditionals arent implemented yet")
            elif expr[0] == "object":
                error("objects arent implemented yet")
