from random import randint
from error import error, debug
from copy import copy
import config

def random_name() -> str:
    return f"RANDOM_{randint(0, 2**20)}"

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
    def __init__(self, name: str, type: str, pointer: Pointer, width: int, manager):
        self.name    = name
        self.type    = type
        self.pointer = pointer
        self.width   = width
        self.manager = manager

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

    def get(self):
        """
        Returns the value pointed to by the var, in a reg, whether or not its already stored in one
        """

        self.update()

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

        
