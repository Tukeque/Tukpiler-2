import var, config
from error import error, debug
import lexer

def consecutive(ls) -> bool:
    return sorted(ls) == list(range(min(ls), max(ls) + 1))

class Manager:
    available_ram: list[int] = list(range(1, config.heap))
    available_reg: list[int] = list(range(1, config.regs))
    var_order: list[var.Var] = []
    vars: dict[str, var.Var] = []
    in_func: bool            = False
    tos: int                 = 0

    header: list[str] = []
    funcs : list[str] = []
    main  : list[str] = []

    def __init__(self, vars: dict[str, var.Var], funcs: dict[str, var.Func], type_to_width: dict[str, int]):
        self.vars  = vars
        self.funcs = funcs
        self.type_to_width = type_to_width

    def get_reg(self, name: str, type: str, is_pointer: bool = False) -> var.Var:
        self.available_reg.sort()

        if len(self.available_reg) >= 1: # has space
            first = self.available_reg.pop(0)
            return self.var(var.Var(name, type, var.Pointer(f"R{first}", "reg"), 1, self, is_pointer=is_pointer))

        else: # no space, must archive
            for i in range(len(self.var_order)):
                if self.var_order[i].pointer.type == "reg":
                    new_pointer = self.var_order[i].archive()

                    return self.var(var.Var(name, type, new_pointer, 1, self, is_pointer=is_pointer))

    def get_mem(self, name: str, type: str, width: int, is_pointer: bool = False) -> var.Var:
        if len(self.available_ram) >= width:
            sort = sorted(self.available_ram)

            if consecutive(sort): # cool and epic
                first = self.available_ram[0]
                self.available_ram = self.available_ram[width:]

                return self.var(var.Var(name, type, var.Pointer(f"M{first}", "ram"), width, self, is_pointer=is_pointer))
            else:
                error("memory didnt free in a way to fit a variable in consecutive addresses") # todo make it check for this in every ram address free and restructure if else
        else:
            error("ran out of memory") # no space (,_,)

    def get_var(self, name: str, type: str, width: int, is_pointer: bool = False) -> var.Var:
        if type != "none":
            return self.get_mem(name, type, width, is_pointer=is_pointer)
        else: # type == "none":
            return self.var(var.Var(name, "none", var.Pointer("M0", "ram"), 1, self, is_pointer=is_pointer))

    def emit(self, x, func: bool = False):
        debug(f"emitting {x}")

        if type(x) == str:
            if not func:
                self.main.append(x)
            else:
                self.funcs.append(x)

        elif type(x) == list:
            if not func:
                self.main += x
            else:
                self.funcs += x

    def return_pointer(self, pointer: var.Pointer):
        if pointer.type == "reg":
            self.available_reg.append(pointer.get_int_addr())
        elif pointer.type == "ram":
            self.available_ram.append(pointer.get_int_addr())

    class Token:
        ops = ["+", "-", "*", "/", "%", "^", "&", "|"]
        unarys = ["~-", "~+", "!"]

        @staticmethod
        def get_associativity(operator) -> str:
            return {
                "+": "both",
                "-": "left",
                "/": "left",
                "*": "both",
                "%": "left",
                "|": "both",
                "&": "both",
                "^": "both",
                "~+": "right",
                "~-": "right",
                "!": "right",
                "**": "both"
            }[operator]

        @staticmethod
        def get_precedence(operator) -> int:
            return {
                "+": 3,
                "-": 3,
                "/": 4,
                "*": 4,
                "%": 4,
                "|": 0,
                "&": 2,
                "^": 1,
                "**": 5,
                "~+": 6,
                "~-": 6,
                "!": 6
            }[operator]

        def __init__(self, type: str, data: list[str], temp_var: bool = None):
            assert type in ["imm", "var", "func", "op", "unary", "paren", "stack"]

            self.type = type
            self.data = data

            if type == "op":
                self.precedence = self.get_precedence(self.get())
                self.associativity = self.get_associativity(self.get())

            self.temp_var = temp_var

        def get(self):
            return self.data[0]

        def __repr__(self):
            return f"{self.type}: {' '.join(self.data)}"

    @classmethod
    def make_tokens(cls, raw: list[str], func_names: list[str], var_names: list[str]) -> lexer.Reader[Token]:
        result: list[cls.Token] = []

        for item in raw:
            if item.isnumeric():
                result.append(cls.Token("imm", [item]))
            elif item in var_names:
                result.append(cls.Token("var", [item]))
            elif item in func_names:
                result.append(cls.Token("func", [item] + raw.until("(", ")", keep=True)))
            elif item in cls.Token.ops:
                result.append(cls.Token("op", [item]))
            elif item in cls.Token.unarys:
                result.append(cls.Token("unary", [item]))
            elif item in ["(", ")"]:
                result.append(cls.Token("paren", [item]))

        return lexer.Reader(result)

    @classmethod
    def shunt(cls, tokens: lexer.Reader[Token]) -> lexer.Reader[Token]: # returns in RPN
        debug(f"shunting {tokens}")
        operators: list[cls.Token] = []
        output   : list[cls.Token] = []

        while not tokens.finished():
            token = tokens.read()

            if token.type in ["imm", "var", "unary"]:
                output.append(token)

            elif token.type == "op":
                while (len(operators) >= 1 and operators[-1].get() != "(") and (operators[-1].precedence > token.precedence or (operators[-1].precedence == token.precedence and token.associativity == "left")):
                    output.append(operators.pop())

                operators.append(token)

            elif token.get() == "(":
                operators.append(token)

            elif token.get() == ")":
                while operators[-1].get() != "(":
                    assert len(operators) != 0 # for debug

                    output.append(operators.pop())

                assert operators[-1].get() == "("
                operators.pop()

                if operators[-1].type == "unary":
                    output.append(operators.pop()) # unambiguaize
        else: # after
            while len(operators) != 0:
                assert operators[-1].get() != "("

                output.append(operators.pop())

        return lexer.Reader(output)

    def emit_rpn(self, rpn: lexer.Reader[Token], ret_var: var.Var, vars: dict[str, var.Var], ret: bool = False):
        debug("emitting rpn")

        if rpn.length() == 0: return ret_var
        operands: list[self.Token] = []

        while not rpn.finished():
            token = rpn.read()
            debug(token)
            
            if token.type in ["var", "imm"]:
                operands.append(token)

            elif token.type == "op":
                b: self.Token = operands.pop()
                a: self.Token = operands.pop()
                result: var.Var = None
                temp            = False

                if not (a.type == "imm" and b.type == "imm"):
                    if config.arch == "urcl":
                        if rpn.finished() == True:
                            # save at ret_var
                            result = ret_var
                        else: # save at temp
                            result = self.get_reg(var.random_name(), "num")
                            temp = True

                        result.op(token.get(), var.Wrapped.from_string(a.get(), vars), var.Wrapped.from_string(b.get(), vars))

                        for x in [a, b]:
                            if x.temp_var is True:
                                self.vars[x.get()].free() # free the var if temp

                    # todo make it figure out if reg (num) or vars stuff (weird and later)
                    # todo silk (stack_top token that is basically ignored)

                    operands.append(self.Token("var", [result.name], temp))
                else: # consts
                    eval(f"operands.append(self.Shunting.Token('imm', [str(int(a.get() {token.get()} int(a.get()))]))")

            elif token.type == "unary":
                x = operands.pop()

                if x.type != "imm":
                    if config.arch == "urcl":
                        temps = []
                        handled = x.value.get(temps)
                        for x in temps: x.free()

                        inst = {
                            "~+": f"AND {handled} &SMAX {handled}",
                            "~-": f"XOR {handled} &MSB {handled}",
                            "!": f"XOR {handled} &MAX {handled}"
                        }[token.get()]

                        self.emit(inst)
                    # todo silk
                else:
                    op = {
                        "~+": "+",
                        "~-": "-",
                        "!": "1 ^ "
                    }[token.get()]
                    eval(f"operands.append(self.Shunting.Token('imm', [ str({op}int(x.get())) ]))")

            debug(operands)

        if not ret:
            token = operands.pop()

            if token.type == "imm":
                if config.arch == "urcl":
                    ret_var.set(var.Wrapped("imm", token.get()))
                # todo silk
            else:
                return ret_var

        return ret_var

    def evaluate(self, tokens: lexer.Reader[Token], vars: dict[str, var.Var], ret_var: var.Var = None, ret: bool = False):
        if ret_var == None:
            ret_var = self.get_reg(var.random_name(), "num") # todo make return var dependant on shunting yard variable correlation (prepass)

        # step 1. forward and null check(and null return)
        if tokens.length() == 1:
            token = tokens.read()
            if token.type == "var":
                return vars[token.get()]


            tokens.decrement() # if didnt return, make readable
        elif tokens.length == 0:
            return ret_var

        # step 2. handle functions() and in-class methods/variables()
        # todo later

        # step 3. shunting yard and emitting the RPN
        rpn = self.shunt(tokens)
        debug(rpn)
        self.emit_rpn(rpn, ret_var, vars, ret)

        # step 4. return and profit
        return ret_var

    def update(self, var: var.Var):
        self.var_order.append(var)
        self.var_order.remove(var)

    def remove(self, var: var.Var):
        self.var_order.remove(var)

    def var(self, var: var.Var) -> var.Var:
        self.var_order.append(var)
        self.vars[var.name] = var
        return var
