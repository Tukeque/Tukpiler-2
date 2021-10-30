from random import randint
from error import error, debug
from copy import copy
import config

def random_salt() -> str:
    return str(randint(0, 2**20))

def random_name() -> str:
    return f"RANDOM_{random_salt()}"

def random_plus_name(name: str) -> str:
    return f"{name}_{random_salt()}"

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

        self.is_temp = False

    def handle(self):
        if self.type == "var":
            var = self.value
            result = var.get()

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

def isfree(var) -> bool:
    return var == None or var.freed

class Var:
    def __init__(self, name: str, type: str, kind: str, pointer: Pointer, width: int, manager):
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
        debug(f"freeing {self.name}")

        if not self.freed:
            for var in self.manager.var_order:
                if var.local == self and self.altered: # this variable is a local of some   variable and the local is different than the variable
                    var.set(Wrapped("var", self))
                else:
                    if self.local != None and self.local.freed != True: # local is allocated, must free too
                        self.local.free()

            if self.pointer.type == "reg":
                self.manager.available_reg.append(self.pointer.get_int_addr())
            else: # self.pointer.type == "ram":
                self.manager.available_ram.append(self.pointer.get_int_addr())

            self.manager.var_order.remove(self)
            self.manager.vars.pop(self.name)

            self.freed = True
        else:
            debug("freed a variable which was already freed (perhaps by ARC)")

    def update(self):
        self.manager.update(self)

    def get(self) -> str: # todo add silk
        self.update()
        result = ""

        if self.pointer.type == "reg":
            if config.arch == "urcl":
                result = self.pointer.addr

        elif self.pointer.type == "ram":
            if config.arch == "urcl":
                if isfree(self.local): # local isnt allocated
                    self.local = self.manager.get_temp("LOCAL")
                    self.local.set(Wrapped("var", self))
                    self.local.altered = False
                else: # local already allocated
                    pass

                result = self.local.pointer.addr

        elif self.pointer.type == "regpoi":
            if config.arch == "urcl":
                if isfree(self.local): # local isnt allocated
                    self.local = self.manager.get_temp(self.references, "LOCAL")
                    self.manager.emit(f"LOD {self.local.pointer.addr} {self.pointer.addr}")
                else: # local already allocated
                    pass

                result = self.local.pointer.addr

        elif self.pointer.type == "mempoi":
            if config.arch == "urcl":
                if isfree(self.local): # local isnt allocated
                    midpoint = self.manager.get_temp()
                    self.manager.emit(f"LOD {midpoint.pointer.addr} {self.pointer.addr}")
                    midpoint.free()

                    self.local = self.manager.get_temp("LOCAL")
                    self.manager.emit(f"LOD {self.local.pointer.addr} {midpoint.pointer.addr}")
                else: # local already allocated
                    pass

                result = self.local.pointer.addr
        
        elif self.pointer.type == "stack":
            if config.arch == "urcl":
                if isfree(self.local): # local isnt allocated
                    self.local = self.manager.get_temp("LOCAL")
                    self.manager.emit(f"LLOD {self.local.pointer.addr} SP {self.pointer.get_int_addr() - self.manager.tos}")
                else:
                    pass

                result = self.local.pointer.addr

        elif self.pointer.type == "stackpoi":
            if config.arch == "urcl":
                if isfree(self.local): # local isnt allocated
                    midpoint = self.manager.get_temp()
                    self.manager.emit(f"LLOD {midpoint.pointer.addr} SP {midpoint.pointer.addr}")
                    midpoint.free()

                    self.local = self.manager.get_temp("LOCAL")
                    self.manager.emit(f"LOD {self.local.pointer.addr} {midpoint.pointer.addr}")
                else:
                    pass

                result = self.local.pointer.addr

        return result

    def set(self, x: Wrapped): # todo stacks
        target = self

        if not isfree(self.local):
            target = self.local

        self.update()

        if x.type == "var":
            var = x.value
            var.update()

            if config.arch == "urcl":
                if target.pointer.type == "ram":
                    if var.pointer.type == "ram":
                        self.manager.emit(f"CPY {target.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "reg":
                        self.manager.emit(f"STR {target.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "mempoi":
                        midpoint = self.manager.get_temp()

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {var.pointer.addr}")
                        self.manager.emit(f"CPY {target.pointer.addr} {midpoint.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "regpoi":
                        self.manager.emit(f"CPY {target.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "stack":
                        pass

                    elif var.pointer.type == "stackpoi":
                        pass

                elif target.pointer.type == "reg":
                    if var.pointer.type == "ram":
                        self.manager.emit(f"LOD {target.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "reg":
                        self.manager.emit(f"MOV {target.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "mempoi":
                        midpoint = self.manager.get_temp()

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {var.pointer.addr}")
                        self.manager.emit(f"LOD {target.pointer.addr} {midpoint.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "regpoi":
                        self.manager.emit(f"LOD {target.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "stack":
                        pass

                    elif var.pointer.type == "stackpoi":
                        pass

                elif target.pointer.type == "mempoi":
                    if var.pointer.type == "ram":
                        midpoint = self.manager.get_temp()

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {target.pointer.addr}")
                        self.manager.emit(f"CPY {midpoint.pointer.addr} {var.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "reg":
                        midpoint = self.manager.get_temp()

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {target.pointer.addr}")
                        self.manager.emit(f"STR {midpoint.pointer.addr} {var.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "mempoi":
                        midpoint1 = self.manager.get_temp()
                        midpoint2 = self.manager.get_temp()

                        self.manager.emit(f"LOD {midpoint1.pointer.addr} {target.pointer.addr}")
                        self.manager.emit(f"LOD {midpoint2.pointer.addr} {var.pointer.addr}")
                        self.manager.emit(f"CPY {midpoint1.pointer.addr} {midpoint2.pointer.addr}")

                        midpoint1.free()
                        midpoint2.free()

                    elif var.pointer.type == "regpoi":
                        midpoint = self.manager.get_temp()

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {target.pointer.addr}")
                        self.manager.emit(f"CPY {midpoint.pointer.addr} {var.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "stack":
                        pass

                    elif var.pointer.type == "stackpoi":
                        pass

                elif target.pointer.type == "regpoi":
                    if var.pointer.type == "ram":
                        self.manager.emit(f"STR {target.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "reg":
                        self.manager.emit(f"CPY {target.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "mempoi":
                        midpoint = self.manager.get_temp()

                        self.manager.emit(f"LOD {midpoint.pointer.addr} {target.pointer.addr}")
                        self.manager.emit(f"CPY {midpoint.pointer.addr} {var.pointer.addr}")

                        midpoint.free()

                    elif var.pointer.type == "regpoi":
                        self.manager.emit(f"CPY {target.pointer.addr} {var.pointer.addr}")

                    elif var.pointer.type == "stack":
                        pass

                    elif var.pointer.type == "stackpoi":
                        pass

                elif target.pointer.type == "stack":
                    pass

                elif target.pointer.type == "stackpoi":
                    pass
            # todo silk

        else: # x.type == "imm":
            imm = x.value

            if config.arch == "urcl":
                if self.pointer.type == "ram":
                    self.manager.emit(f"STR {self.pointer.addr} {imm}")

                elif self.ptargetinter.type == "reg":
                    self.manager.emit(f"IMM {self.pointer.addr} {imm}")

                elif self.pointer.type == "mempoi":
                    midpoint = self.manager.get_temp()

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

    def op(self, op: str, src1: Wrapped, src2: Wrapped):
        self.manager.emit(f"// {self.name} = {src1.value if type(src1.value) is str else src1.value.name} {op} {src2.value if type(src2.value) is str else src2.value.name}")

        target = self

        if not isfree(self.local):
            target = self.local
        elif self.pointer.type != "reg": # local isnt allocated and need local
            #//self.get()
            #^ nope because we want to allocate the local but not get the value in there
            self.local = self.manager.get_temp("LOCAL")
            target = self.local

        if config.arch == "urcl":
            if target.pointer.type == "reg":
                # handle
                handled1 = src1.handle() # it isnt necesary to put the hold but its nice i guess
                if src1.value == src2.value:
                    handled2 = handled1
                else:
                    handled2 = src2.handle()

                debug(f"op {self.name}({self.pointer.addr}) = {op} {[handled1, handled2]}")
                self.manager.emit(f"{op_to_urcl[op]} {target.pointer.addr} {handled1} {handled2}")
            else:
                temp = self.manager.get_temp()
                temp.op(op, src1, src2)
                target.set(Wrapped("var", temp))
                temp.free()
        # todo silk

        self.altered = True

class Func:
    def __init__(self, name, args, return_type, manager):
        self.name = name
        self.args: list[list[str]] = args
        self.return_type = return_type
        self.manager = manager
        self.returnpoi = Pointer(f"S{manager.tos}", "stack")

        self.used_regs: list[str] = []
        self.archived_regs: dict[str, str] = {}
        self.salt = random_salt()

    def finish(self, reg_use: list[int]):
        reg_use.reverse()
        self.manager.emit(["LSTR SP -2 0", f".return_{self.name}_{self.salt}"]) # default return 0(null)
        self.manager.emit("\n".join(["POP R0" for _ in range(0, len(self.args))]))
        self.manager.emit("\n".join([f"POP R{x}" for x in reg_use if x != 1]))
        self.manager.emit(["JMP R1", f".end_{self.name}_{self.salt}"])
        reg_use.reverse()

        for i, line in enumerate(self.manager.header):
            if line == "@INSERTSAVE":
                self.manager.header[i] = "\n".join([f"PSH R{x}" for x in reg_use if x != 1])
                return

    def header(self):
        self.manager.emit([f".save_{self.name}_{self.salt}", "POP R1", "@INSERTSAVE", "JMP R1"])
        self.manager.emit([f".func_{self.name}_{self.salt}", "POP R1"])

        self.args.reverse()

        for arg in self.args:
            self.manager.get_stack(arg[1], arg[0], self.manager.type_to_width[arg[0]])

        self.args.reverse() # restore args
