from random import randint
from error import error, debug
from copy import copy
import config

def random_salt() -> str:
    return str(randint(0, 2**20))

def random_name() -> str:
    return f"RANDOM_{random_salt()}"

op_to_urcl = {
    "+": "ADD",
    "-": "SUB",
    "*": "MLT",
    "/": "DIV",
    "%": "MOD",
    "|": "OR" ,
    "&": "AND",
    "^": "XOR"
}

class Wrapped:
    def __init__(self, type: str, value):
        assert type in ["var", "imm"]

        self.type = type
        self.value = value

    def handle(self):
        if self.type == "var":
            var = self.value
            var.update()

            temps = []
            result = var.get(temps)
            for x in temps: x.free()

            return result
        else: # self.type == "imm":
            return self.value

    def from_string(x: str, vars: dict):
        if x in vars:
            return Wrapped("var", vars[x])
        else:
            return Wrapped("imm", x)

class Pointer:
    def __init__(self, addr: str, type: str):
        assert type in ["reg", "ram", "mempoi", "regpoi", "stackpoi", "stack"]

        self.addr = addr # MX, RX or SX (M1, R1, S1 for example)
        self.type = type

    def get_int_addr(self):
        return int(self.addr[1:])

class Var:
    def __init__(self, name: str, type: str, kind: str, pointer: Pointer, width: int, references: int, manager):
        assert kind in ["var", "temp"]

        self.name    = name
        self.type    = type
        self.kind    = kind
        self.pointer = pointer
        self.local   = None

        self.width   = width
        self.manager = manager
        self.freed   = False
        self.altered = False
        self.references = references

    def archive(self):
        if self.pointer.type == "reg":
            new = self.manager.get_mem(random_name(), self.type, self.width)

            new.set(Wrapped("var", self)) # new = self(value)
            old_pointer = copy(self.pointer) # copy old pointer
            self.pointer = new.pointer # self = new 

            self.manager.remove(new)

            return old_pointer

        else:
            error("trying to archive non reg variable")

    def unarchive(self):
        pass # todo

    def free(self):
        if self.pointer.type == "reg":
            self.manager.available_reg.append(self.pointer.get_int_addr())
        else: # self.pointer.type == "ram":
            self.manager.available_ram.append(self.pointer.get_int_addr())

        self.manager.var_order.remove(self)
        self.manager.vars.pop(self.name)

        self.freed = True

    def update(self):
        self.manager.update(self)

    def reference(self):
        self.references -= 1
        if self.references <= 0:
            for var in self.manager.var_order:
                if var.local == self and self.altered: # this variable is a local of some variable and the local is different than the variable
                    var.set(Wrapped("var", self))

            self.free() # wont be used anymore, free

    def get(self) -> str: # todo add silk
        self.update()
        result = ""

        def isfree(var) -> bool:
            return var == None or var.freed

        if self.pointer.type == "reg":
            if config.arch == "urcl":
                result = self.pointer.addr

        elif self.pointer.type == "ram":
            if config.arch == "urcl":
                if isfree(self.local): # local isnt allocated
                    self.local = self.manager.get_reg(random_name(), "num") # todo get_temp()
                    self.local.set(Wrapped("var", self))
                    self.local.altered = False
                else: # local already allocated
                    pass

                result = self.local.pointer.addr

        elif self.pointer.type == "regpoi":
            if config.arch == "urcl":
                if isfree(self.local): # local isnt allocated
                    self.local = self.manager.get_reg(random_name(), "num")
                    self.manager.emit(f"LOD {self.local.pointer.addr} {self.pointer.addr}")
                else: # local already allocated
                    pass

                result = self.local.pointer.addr

        elif self.pointer.type == "mempoi":
            if config.arch == "urcl":
                if isfree(self.local): # local isnt allocated
                    midpoint = self.manager.get_reg(random_name(), "num")
                    self.manager.emit(f"LOD {midpoint.pointer.addr} {self.pointer.addr}")
                    midpoint.free()

                    self.local = self.manager.get_reg(random_name(), "num")
                    self.manager.emit(f"LOD {self.local.pointer.addr} {midpoint.pointer.addr}")
                else: # local already allocated
                    pass

                result = self.local.pointer.addr
        
        elif self.pointer.type == "stack":
            if config.arch == "urcl":
                if isfree(self.local): # local isnt allocated
                    self.local = self.manager.get_reg(random_name(), "num")
                    self.manager.emit(f"LLOD {self.local.pointer.addr} SP {self.pointer.get_int_addr() - self.manager.tos}")
                else:
                    pass

                result = self.local.pointer.addr

        elif self.pointer.type == "stackpoi":
            if config.arch == "urcl":
                if isfree(self.local): # local isnt allocated
                    midpoint = self.manager.get_reg(random_name(), "num")
                    self.manager.emit(f"LLOD {midpoint.pointer.addr} SP {midpoint.pointer.addr}")
                    midpoint.free()

                    self.local = self.manager.get_reg(random_name(), "num")
                    self.manager.emit(f"LOD {self.local.pointer.addr} {midpoint.pointer.addr}")
                else:
                    pass

                result = self.local.pointer.addr

        self.reference()
        return result

    def set(self, x: Wrapped): # todo stacks

        if x.type == "var":
            var = x.value
            
            self.update(); var.update()

            if config.arch == "urcl":
                if self.pointer.type == "ram":
                    if var.pointer.type == "ram":
                        self.manager.emit(f"CPY {self.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "reg":
                        self.manager.emit(f"STR {self.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "mempoi":
                        midpoint = self.manager.get_reg(random_name(), "num")

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {var.pointer.addr}")
                        self.manager.emit(f"CPY {self.pointer.addr} {midpoint.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "regpoi":
                        self.manager.emit(f"CPY {self.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "stack":
                        pass

                    elif var.pointer.type == "stackpoi":
                        pass

                elif self.pointer.type == "reg":
                    if var.pointer.type == "ram":
                        self.manager.emit(f"LOD {self.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "reg":
                        self.manager.emit(f"MOV {self.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "mempoi":
                        midpoint = self.manager.get_reg(random_name(), "num")

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {var.pointer.addr}")
                        self.manager.emit(f"LOD {self.pointer.addr} {midpoint.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "regpoi":
                        self.manager.emit(f"LOD {self.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "stack":
                        pass

                    elif var.pointer.type == "stackpoi":
                        pass

                elif self.pointer.type == "mempoi":
                    if var.pointer.type == "ram":
                        midpoint = self.manager.get_reg(random_name(), "num")

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {self.pointer.addr}")
                        self.manager.emit(f"CPY {midpoint.pointer.addr} {var.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "reg":
                        midpoint = self.manager.get_reg(random_name(), "num")

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {self.pointer.addr}")
                        self.manager.emit(f"STR {midpoint.pointer.addr} {var.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "mempoi":
                        midpoint1 = self.manager.get_reg(random_name(), "num")
                        midpoint2 = self.manager.get_reg(random_name(), "num")

                        self.manager.emit(f"LOD {midpoint1.pointer.addr} {self.pointer.addr}")
                        self.manager.emit(f"LOD {midpoint2.pointer.addr} {var.pointer.addr}")
                        self.manager.emit(f"CPY {midpoint1.pointer.addr} {midpoint2.pointer.addr}")

                        midpoint1.free()
                        midpoint2.free()

                    elif var.pointer.type == "regpoi":
                        midpoint = self.manager.get_reg(random_name(), "num")

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {self.pointer.addr}")
                        self.manager.emit(f"CPY {midpoint.pointer.addr} {var.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "stack":
                        pass

                    elif var.pointer.type == "stackpoi":
                        pass

                elif self.pointer.type == "regpoi":
                    if var.pointer.type == "ram":
                        self.manager.emit(f"STR {self.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "reg":
                        self.manager.emit(f"CPY {self.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "mempoi":
                        midpoint = self.manager.get_reg(random_name(), "num")

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {self.pointer.addr}")
                        self.manager.emit(f"CPY {midpoint.pointer.addr} {var.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "regpoi":
                        self.manager.emit(f"CPY {self.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "stack":
                        pass

                    elif var.pointer.type == "stackpoi":
                        pass

                elif self.pointer.type == "stack":
                    pass

                elif self.pointer.type == "stackpoi":
                    pass
            # todo silk

        else: # x.type == "imm":
            imm = x.value

            if config.arch == "urcl":
                if self.pointer.type == "ram":
                    self.manager.emit(f"STR {self.pointer.addr} {imm}")

                elif self.pointer.type == "reg":
                    self.manager.emit(f"IMM {self.pointer.addr} {imm}")

                elif self.pointer.type == "mempoi":
                    midpoint = self.manager.get_reg(random_name(), "num")

                    self.manager.emit(f"LOD {midpoint.pointer.addr} {self.pointer.addr}")
                    self.manager.emit(f"STR {midpoint.pointer.addr} {imm}")

                    midpoint.free()

                elif self.pointer.type == "regpoi":
                    self.manager.emit(f"STR {self.pointer.addr} {imm}")

                elif self.pointer.type == "stack":
                    pass

                elif self.pointer.type == "stackpoi":
                    pass
            # todo silk

        self.altered = True

    def op(self, op: str, src1: Wrapped, src2: Wrapped): # todo
        temps = []
        handled1 = src1.handle()

        if src1.value == src2.value:
            handled2 = handled1
        handled2 = src2.handle()

        if config.arch == "urcl":
            if self.pointer.type == "ram":
                temp = self.manager.get_reg(random_name(), "num")
                temp.op(op, src1, src2)
                self.set(Wrapped("var", temp))
            else: # self.pointer.type == "reg":
                debug([handled1, handled2])
                self.manager.emit(f"{op_to_urcl[op]} {self.pointer.addr} {handled1} {handled2}")
        # todo silk

        for var in temps:
            var.free()

    def push(self):
        self.update()
        self.manager.tos += 1

        if self.is_pointer:
            if config.arch == "urcl":
                if self.pointer.type == "ram" and self.type == "num":
                    temp = self.manager.get_reg(random_name(), "num")
                    temp.set(Wrapped("var", self))

                    self.manager.emit(f"PSH {temp.pointer.addr}")

                else: # self.pointer.type == "reg" or "ram":
                    self.manager.emit(f"PSH {self.pointer.addr}")
            # todo silk

    def pop(self):
        self.update()
        self.manager.tos -= 1

        if config.arch == "urcl":
            if self.pointer.type == "ram":
                temp = self.manager.get_reg(random_name(), "num")
            
                self.manager.emit(f"POP {temp.pointer.addr}")
                self.set(Wrapped("var", temp))

            else: # self.pointer.type == "reg":
                self.manager.emit(f"POP {self.pointer.addr}")
        # todo silk

class Func: # todo remake
    def __init__(self, name, args, return_type, manager):
        self.name = name
        self.args: list[list[str]] = args
        self.return_type = return_type
        self.manager = manager

        self.used_regs: list[str] = []
        self.archived_regs: dict[str, str] = {}
        self.salt = random_salt()

    def save(self) -> list[str]:
        urcl = [f".save_{self.name}_{self.salt}", "POP R1"]

        for reg in self.used_regs:
            urcl.append(f"PSH {reg}")

        return urcl

    def restore(self) -> list[str]:
        urcl = []

        for reg in self.archived_regs:
            urcl.append(f"LOD {reg} {self.archived_regs[reg]}")

        return urcl

    def header(self): # oops
        self.manager.emit([f"func_{self.name}_{self.salt}", "POP R1"])

        self.args.reverse()

        for arg in self.args:
            x = self.manager.get_var(arg[1], arg[0], self.manager.type_to_width[arg[0]], True if arg[0] != "num" or "none" else False)
            x.pop()

        self.args.reverse()
