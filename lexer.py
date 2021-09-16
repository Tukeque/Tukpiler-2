from typing import Generic, TypeVar
from error import error

T = TypeVar("T")

class Reader(Generic[T]):
    def __init__(self, elements: list[T]):
        self.elements = elements
        self.pointer = 0

    def read(self) -> T:
        self.pointer += 1
        return self.elements[self.pointer - 1]

    def finished(self) -> bool:
        if self.pointer >= len(self.elements):
            return True
        return False

    def length(self) -> int:
        return len(self.elements)

    def until(self, enter: str, exit: str, keep: bool = False):
        level  = 0
        inside = False
        result: list[T] = []

        while not self.finished():
            item = self.read()

            print(item)

            if inside:
                if item == enter:
                    level += 1

                if item == exit and keep is False:
                    level -= 1

                if level == 0:
                    if keep is False:
                        self.decrement() # to make it so you can still read the top later
                    break

                if item == exit and keep is True:
                    level -= 1

                    if level == 0: # skip
                        result.append(item)
                        break

                result.append(item)

            if item == enter:
                level += 1
                inside = True

                if keep:
                    result.append(item)
        if level != 0: # hasn't properly exited
            error("Reader failed to find an until()")

        print(result)

        return result

    def decrement(self):
        self.pointer -= 1

        if self.pointer == -1:
            error("decremented pointer to -1 in a Reader()")

    def reset(self):
        self.pointer = 0
        return self

    def __repr__(self) -> str:
        return "[" + ", ".join([repr(x) for x in self.elements]) + "]"

    def split(self, splitter: T) -> list[list[T]]:
        result = [[]]

        for item in self.elements:
            if item == splitter:
                result.append([])
            else:
                result[-1].append(item)

        return result

class Lexer:
    def __init__(self, separators: list[str], style, joiner: str = ";", strings: list[str] = ['"', "'"], comments: bool = True, comment_tokens: list[str] = ["#", "//"], multi_comment_tokens: list[list[str]] = [["/*", "*/"], ["///", "///"], ['"""', '"""']]):
        self.separators = separators
        self.joiner = joiner
        self.strings = strings

        self.style = style

        self.comments = comments
        self.comment_tokens = comment_tokens
        self.multi_comment_tokens = multi_comment_tokens

    def remove_comments(self, raw: list[str]) -> list[str]:
        for i, line in enumerate(raw):
            raw[i] = line.replace("\n", "")

            for comment_token in self.comment_tokens:
                if line.count(comment_token) >= 1:
                    raw[i] = line[:line.index(comment_token)] # remove comment

        return raw

    def multi_remove_comments(self, tokens: Reader) -> Reader:
        result: list[str] = []

        while not tokens.finished():
            token = tokens.read()

            commented = False

            for multi_comment_token in self.multi_comment_tokens:
                if token == multi_comment_token[0]:
                    tokens.until(multi_comment_token[0], multi_comment_token[1], True)
                    commented = True
            else:
                if not commented:
                    result.append(token)

        return Reader(result)

    def syntax_check(self, tokens: Reader) -> Reader:
        """
        will return with no errors if syntax is correct
        """
        # TODO check syntax based on self.style
        
        return tokens.reset()

    def lex(self, raw: list[str]) -> Reader: # TODO replace unary
        def is_something(x: str):
            return (token.replace(" ", "").replace(self.joiner, "") != "")

        if self.comments:
            code = self.remove_comments(raw)
        else:
            code = raw

        stream = Reader(self.joiner.join(code))
        tokens: list[str] = []
        token  = ""

        while not stream.finished():
            char = stream.read()

            if char in self.strings: # handle strings
                if is_something(token):
                    tokens.append(token)
                token = ""

                tokens.append("".join(stream.until(char, char, True)))
            elif char in self.separators: # if not string, handle separators
                if is_something(token):
                    tokens.append(token)
                    token = ""

                if char != " ":
                    tokens.append(char)

            elif char != " ": # else, continue constructing token
                token += char

                if token in self.separators: # token is fully found
                    tokens.append(token)
                    token = ""

        tokens.append(token)

        # tokens is now constructed

        if self.comments: # remove multiline comments
            result = self.multi_remove_comments(Reader(tokens))
        else:
            result = Reader(tokens)

        result = self.syntax_check(result) # syntax check
        return result
                