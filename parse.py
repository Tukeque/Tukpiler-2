from lexer import Reader
from rich import print

class Parser:
    def __init__(self, tokens: Reader[str]):
        self.tokens = tokens

    def parse(self) -> Reader[list[str]]:
        print(f"parsing {self.tokens}")

        expr: list[str] = []
        total: list[list[str]] = []

        self.tokens.elements.append(";")

        while not self.tokens.finished():
            token = self.tokens.read()

            if token == "function" or token == "object":
                assert expr == []

                self.tokens.decrement()
                expr = [token] + self.tokens.until(token, "{") + self.tokens.until("{", "}", keep=True)
                total.append(expr)
                expr = []

            # todo if else and elif

            elif token == ";":
                if expr != []:
                    total.append(expr)
                    expr = []
            
            else:
                expr.append(token)

        return Reader(total)
