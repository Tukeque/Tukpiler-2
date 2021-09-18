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

            return var.get()
        else: # self.type == "imm":
            return self.value

    def from_string(x: str, vars: dict):
        if x in vars:
            return Wrapped("var", vars[x])
        else:
            return Wrapped("imm", x)

class Pointer:
    def __init__(self, addr: str, type: str):
        assert type in ["reg", "ram"]

        self.addr = addr
        self.type = type

    def get_int_addr(self):
        return int(self.addr[1:])

class Var:
    def __init__(self, name: str, type: str, pointer: Pointer, width: int, manager, is_pointer: bool = False):
        self.name    = name
        self.type    = type
        self.pointer = pointer
        self.width   = width
        self.manager = manager

        self.is_pointer = is_pointer

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

    def update(self):
        self.manager.update(self)

    def get(self): # updated for pointers
        """
        Returns the value pointed to by the var, in a reg, whether or not its already stored in one
        """

        self.update()

        if self.is_pointer:
            if config.arch == "urcl":
                if self.pointer.type == "reg":
                    result = self.manager.get_reg(self.pointer, "num")
                    self.manager.emit(f"LOD {result.pointer.addr} {self.pointer.addr}")

                    return result.pointer.addr

                else: # self.pointer.type == "ram":
                    local = self.manager.get_reg(self.pointer, "num")
                    local.set(Wrapped("var", self)) # copy to local

                    result = self.manager.get_reg(self.pointer, "num")
                    self.manager.emit(f"LOD {result.pointer.addr} {self.pointer.addr}")

                    return result.pointer.addr
        else:
            if config.arch == "urcl":
                if self.pointer.type == "reg":
                    return self.pointer.addr

                else: # self.pointer.type == "ram":
                    local = self.manager.get_reg(self.pointer, "num")
                    local.set(Wrapped("var", self)) # copy to local

                    return local.get()
            # todo silk

    def set(self, x: Wrapped):
        if x.type == "var":
            var = x.value
            
            for x in [self, var]: x.update()

            if config.arch == "urcl":
                if self.pointer.type == "ram":
                    if var.pointer.type == "ram":   op = "CPY"
                    elif var.pointer.type == "reg": op = "STR"
                elif self.pointer.type == "reg":
                    if var.pointer.type == "ram":   op = "LOD"
                    elif var.pointer.type == "reg": op = "MOV"

                self.manager.emit(f"{op} {self.pointer.addr} {var.pointer.addr}")
            # todo silk

        else: # x.type == "imm":
            imm = x.value

            if config.arch == "urcl":
                if self.pointer.type == "ram":   op = "STR"
                elif self.pointer.type == "reg": op = "STR"
                
                self.manager.emit(f"{op} {self.pointer.addr} {imm}")
            # todo silk

    def op(self, op: str, src1: Wrapped, src2: Wrapped):
        temps = []
        handled1 = src1.handle()
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

class Func:
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
