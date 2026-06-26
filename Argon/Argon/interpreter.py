# -*- coding: utf-8 -*-
"""
TurkCode interpreter.

This version replaces the previous multi-version concatenated file with a
single parser/evaluator based implementation. The goal is to keep the language
coherent and actually executable instead of advertising features that do not
work together.
"""

from __future__ import annotations

import datetime as dt
import importlib
import json
import math
import os
import random
import re
import sys
import types
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


class TurkCodeError(Exception):
    """Base error for TurkCode."""

    def __init__(
        self,
        message: str,
        *,
        filename: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ):
        super().__init__(message)
        self.message = message
        self.filename = filename
        self.line = line
        self.column = column

    def __str__(self) -> str:
        location = []
        if self.filename and self.filename != "<girdi>":
            location.append(self.filename)
        if self.line is not None:
            line_info = f"Satir {self.line}"
            if self.column is not None:
                line_info += f", sutun {self.column}"
            location.append(line_info)
        if not location:
            return self.message
        return f"{' - '.join(location)}: {self.message}"


class TurkCodeSyntaxError(TurkCodeError):
    """Syntax error."""


class TurkCodeRuntimeError(TurkCodeError):
    """Runtime error."""


@dataclass
class Token:
    type: str
    lexeme: str
    literal: Any
    line: int
    column: int


KEYWORDS = {
    "degisken": "DEGISKEN",
    "değişken": "DEGISKEN",
    "fonksiyon": "FONKSIYON",
    "sinif": "SINIF",
    "sınıf": "SINIF",
    "eger": "EGER",
    "eğer": "EGER",
    "degilse": "DEGILSE",
    "değilse": "DEGILSE",
    "dongu": "DONGU",
    "döngü": "DONGU",
    "while": "WHILE",
    "yap": "YAP",
    "her": "HER",
    "in": "IN",
    "ithal": "ITHAL",
    "olarak": "OLARAK",
    "dondur": "DONDUR",
    "döndür": "DONDUR",
    "don": "DONDUR",
    "dön": "DONDUR",
    "devam": "DEVAM",
    "break": "BREAK",
    "dur": "BREAK",
    "sec": "SEC",
    "seç": "SEC",
    "durum": "DURUM",
    "varsayilan": "VARSAYILAN",
    "varsayılan": "VARSAYILAN",
    "dene": "DENE",
    "yakala": "YAKALA",
    "firlat": "FIRLAT",
    "fırlat": "FIRLAT",
    "dogru": "BOOL",
    "doğru": "BOOL",
    "yanlis": "BOOL",
    "yanlış": "BOOL",
    "bos": "NULL",
    "boş": "NULL",
    "ve": "VE",
    "veya": "VEYA",
    "degil": "DEGIL",
    "değil": "DEGIL",
    "this": "THIS",
    "yeni": "YENI",
}


PROPERTY_NAME_TOKENS = {
    "IDENT",
    *(token for token in set(KEYWORDS.values()) if token not in {"BOOL", "NULL"}),
}

TURKISH_TRANSLATION_TABLE = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "i": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "Ç": "c",
        "Ğ": "g",
        "I": "i",
        "İ": "i",
        "Ö": "o",
        "Ş": "s",
        "Ü": "u",
    }
)

PYTHON_MODULE_ALIASES = {
    "matematik": "math",
    "rastgele": "random",
    "tarihsaat": "datetime",
    "tarihvesaat": "datetime",
    "zaman": "time",
    "sistem": "sys",
    "isletim": "os",
    "isletimsistemi": "os",
    "yol": "pathlib",
    "dosyayolu": "pathlib",
    "duzenliifade": "re",
    "regex": "re",
    "istatistik": "statistics",
    "kesir": "fractions",
    "ondalik": "decimal",
    "kopya": "copy",
    "csv": "csv",
    "json": "json",
    "web": "urllib.request",
    "temel": "builtins",
}

PYTHON_MEMBER_ALIASES = {
    "abs": ("mutlak",),
    "all": ("hepsi",),
    "any": ("herhangi",),
    "append": ("ekle",),
    "capitalize": ("ilkHarfBuyuk", "ilkHarfBüyük"),
    "ceil": ("yuvarlaYukari", "yuvarlaYukarı"),
    "choice": ("sec", "seç"),
    "choices": ("secimler", "seçimler"),
    "clear": ("temizle",),
    "copy": ("kopyala",),
    "count": ("say",),
    "date": ("tarih",),
    "datetime": ("tarihSaat",),
    "degrees": ("dereceyeCevir", "dereceyeÇevir"),
    "dump": ("dosyayaYaz",),
    "dumps": ("donustur", "dönüştür"),
    "endswith": ("bitir", "sonuMu"),
    "exists": ("varMi", "varMı"),
    "extend": ("genislet", "genişlet"),
    "factorial": ("faktoriyel",),
    "fabs": ("mutlak",),
    "find": ("bul",),
    "findall": ("hepsiniBul",),
    "floor": ("yuvarlaAsagi", "yuvarlaAşağı"),
    "format": ("formatla",),
    "get": ("al", "getir"),
    "getcwd": ("calismaDizini", "çalışmaDizini"),
    "glob": ("desenleBul",),
    "is_dir": ("klasorMu", "klasörMü"),
    "is_file": ("dosyaMi", "dosyaMı"),
    "isclose": ("yakinMi", "yakınMı"),
    "join": ("birlestir", "birleştir"),
    "lcm": ("okek",),
    "listdir": ("listele",),
    "loads": ("coz", "çöz"),
    "lower": ("kucukHarf", "küçükHarf"),
    "makedirs": ("klasorleriOlustur", "klasörleriOluştur"),
    "match": ("esles", "eşleş"),
    "mean": ("ortalama",),
    "median": ("ortanca",),
    "mkdir": ("klasorOlustur", "klasörOluştur"),
    "mode": ("tepeDeger", "tepeDeğer"),
    "now": ("simdi", "şimdi"),
    "open": ("ac", "aç"),
    "pop": ("cikar", "çıkar"),
    "pow": ("us", "üs"),
    "radians": ("radyanaCevir", "radyanaÇevir"),
    "randint": ("rastgeleTam",),
    "random": ("rastgele",),
    "read": ("oku",),
    "read_text": ("metinOku", "okuMetin"),
    "remove": ("sil",),
    "rename": ("yenidenAdlandir", "yenidenAdlandır"),
    "replace": ("degistir", "değiştir"),
    "round": ("yuvarla",),
    "sample": ("orneklem", "örneklem"),
    "search": ("ara",),
    "seed": ("tohum",),
    "shuffle": ("karistir", "karıştır"),
    "split": ("parcala", "parçala"),
    "sqrt": ("karekok", "karekök"),
    "startswith": ("basla", "başla"),
    "stdev": ("standartSapma",),
    "sub": ("degistir", "değiştir"),
    "time": ("saat", "zaman"),
    "timedelta": ("zamanFarki", "zamanFarkı"),
    "today": ("bugun", "bugün"),
    "uniform": ("rastgeleOndalik", "rastgeleOndalık"),
    "upper": ("buyukHarf", "büyükHarf"),
    "variance": ("varyans",),
    "write": ("yaz",),
    "write_text": ("metinYaz", "yazMetin"),
}

PYTHON_WORD_ALIASES = {
    "all": "hepsi",
    "append": "ekle",
    "choice": "sec",
    "clear": "temizle",
    "copy": "kopyala",
    "count": "say",
    "date": "tarih",
    "dir": "klasor",
    "exists": "varMi",
    "file": "dosya",
    "find": "bul",
    "format": "formatla",
    "get": "al",
    "is": "mi",
    "join": "birlestir",
    "list": "liste",
    "load": "yukle",
    "loads": "coz",
    "lower": "kucuk",
    "make": "olustur",
    "mean": "ortalama",
    "mkdir": "klasorOlustur",
    "open": "ac",
    "path": "yol",
    "random": "rastgele",
    "read": "oku",
    "remove": "sil",
    "replace": "degistir",
    "search": "ara",
    "split": "parcala",
    "text": "metin",
    "time": "zaman",
    "upper": "buyuk",
    "write": "yaz",
}


def _normalize_identifier_name(name: str) -> str:
    translated = name.translate(TURKISH_TRANSLATION_TABLE)
    decomposed = unicodedata.normalize("NFKD", translated)
    ascii_like = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^0-9A-Za-z]+", "", ascii_like).lower()


def _split_python_identifier(name: str) -> List[str]:
    parts: List[str] = []
    for chunk in re.split(r"_+", name):
        if not chunk:
            continue
        parts.extend(re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", chunk) or [chunk])
    return [part.lower() for part in parts]


def _lower_camel(words: Sequence[str]) -> str:
    if not words:
        return ""
    return words[0] + "".join(word[:1].upper() + word[1:] for word in words[1:])


def _python_alias_candidates(actual_name: str) -> set[str]:
    aliases = set(PYTHON_MEMBER_ALIASES.get(actual_name, ()))
    words = _split_python_identifier(actual_name)
    translated_words = [PYTHON_WORD_ALIASES.get(word, word) for word in words]
    if translated_words and translated_words != words:
        aliases.add(_lower_camel(translated_words))
        aliases.add("_".join(translated_words))
    return {alias for alias in aliases if alias}


def _build_python_member_alias_map(obj: Any) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    try:
        names = dir(obj)
    except Exception:
        return aliases

    for actual_name in names:
        if actual_name.startswith("_"):
            continue
        aliases.setdefault(actual_name, actual_name)
        aliases.setdefault(_normalize_identifier_name(actual_name), actual_name)
        for alias in _python_alias_candidates(actual_name):
            aliases.setdefault(alias, actual_name)
            aliases.setdefault(_normalize_identifier_name(alias), actual_name)
    return aliases


def _resolve_python_member_name(obj: Any, name: str) -> Optional[str]:
    try:
        if hasattr(obj, name):
            return name
    except Exception:
        pass
    aliases = _build_python_member_alias_map(obj)
    return aliases.get(name) or aliases.get(_normalize_identifier_name(name))


def _normalize_python_module_name(name: str) -> str:
    raw_name = str(name).strip()
    alias_key = _normalize_identifier_name(raw_name)
    module_name = PYTHON_MODULE_ALIASES.get(alias_key, raw_name)
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$", module_name):
        raise TurkCodeRuntimeError(f"Gecersiz Python kutuphanesi adi: {raw_name}")
    return module_name


def _syntax_error(
    line: int,
    column: int,
    message: str,
    filename: Optional[str] = None,
) -> TurkCodeSyntaxError:
    return TurkCodeSyntaxError(message, filename=filename, line=line, column=column)


def normalize_source(source: str) -> str:
    """
    Insert semicolons at line endings when the user omits them for simple
    statements. This keeps the parser small while preserving familiar syntax.

    It intentionally does not try to infer semicolons after multi-line object
    literals that end with a bare `}`. The bundled examples already terminate
    those blocks with `;`, which keeps the behavior predictable.
    """

    source = source.replace("\r\n", "\n").replace("\r", "\n")
    output: List[str] = []
    quote: Optional[str] = None
    escape = False
    block_comment = False
    line_comment = False
    paren_depth = 0
    bracket_depth = 0

    def previous_significant_char() -> Optional[str]:
        for char in reversed(output):
            if char == "\n":
                return None
            if not char.isspace():
                return char
        return None

    i = 0
    while i < len(source):
        char = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""

        if line_comment:
            if char == "\n":
                prev = previous_significant_char()
                if prev and prev not in ";{:,}":
                    output.append(";")
                output.append("\n")
                line_comment = False
            i += 1
            continue

        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                i += 2
            else:
                if char == "\n":
                    output.append("\n")
                i += 1
            continue

        if quote is not None:
            output.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = None
            i += 1
            continue

        if char == "/" and nxt == "*":
            block_comment = True
            i += 2
            continue

        if char == "/" and nxt == "/":
            line_comment = True
            i += 2
            continue

        if char in ("'", '"'):
            quote = char
            output.append(char)
            i += 1
            continue

        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth = max(0, paren_depth - 1)
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth = max(0, bracket_depth - 1)

        if char == "\n":
            prev = previous_significant_char()
            if paren_depth == 0 and bracket_depth == 0 and prev and prev not in ";{:,}":
                output.append(";")
            output.append("\n")
            i += 1
            continue

        output.append(char)
        i += 1

    if line_comment:
        prev = previous_significant_char()
        if prev and prev not in ";{:,}":
            output.append(";")

    prev = previous_significant_char()
    if prev and prev not in ";{:,}":
        output.append(";")

    return "".join(output)


class Lexer:
    def __init__(self, source: str, filename: str = "<girdi>"):
        self.source = source
        self.filename = filename
        self.length = len(source)
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        while not self._is_at_end():
            start_line = self.line
            start_col = self.column
            char = self._advance()

            if char in " \t":
                continue

            if char == "\n":
                continue

            if char.isdigit():
                self._number(char, start_line, start_col)
                continue

            if self._is_identifier_start(char):
                self._identifier(char, start_line, start_col)
                continue

            if char in ('"', "'"):
                self._string(char, start_line, start_col)
                continue

            one_char_tokens = {
                "(": "LPAREN",
                ")": "RPAREN",
                "{": "LBRACE",
                "}": "RBRACE",
                "[": "LBRACKET",
                "]": "RBRACKET",
                ",": "COMMA",
                ".": "DOT",
                ";": "SEMICOLON",
                ":": "COLON",
                "?": "QUESTION",
                "+": "PLUS",
                "-": "MINUS",
                "*": "STAR",
                "/": "SLASH",
                "%": "PERCENT",
                "^": "CARET",
                "=": "EQUAL",
                "!": "BANG",
                ">": "GT",
                "<": "LT",
            }

            if char == "+" and self._match("+"):
                self._add("PLUS_PLUS", "++", None, start_line, start_col)
                continue
            if char == "-" and self._match("-"):
                self._add("MINUS_MINUS", "--", None, start_line, start_col)
                continue
            if char == "=" and self._match("="):
                self._add("EQEQ", "==", None, start_line, start_col)
                continue
            if char == "!" and self._match("="):
                self._add("BANGEQ", "!=", None, start_line, start_col)
                continue
            if char == ">" and self._match("="):
                self._add("GTE", ">=", None, start_line, start_col)
                continue
            if char == "<" and self._match("="):
                self._add("LTE", "<=", None, start_line, start_col)
                continue
            if char == "+" and self._match("="):
                self._add("PLUS_EQUAL", "+=", None, start_line, start_col)
                continue
            if char == "-" and self._match("="):
                self._add("MINUS_EQUAL", "-=", None, start_line, start_col)
                continue
            if char == "*" and self._match("="):
                self._add("STAR_EQUAL", "*=", None, start_line, start_col)
                continue
            if char == "/" and self._match("="):
                self._add("SLASH_EQUAL", "/=", None, start_line, start_col)
                continue
            if char == "%" and self._match("="):
                self._add("PERCENT_EQUAL", "%=", None, start_line, start_col)
                continue
            if char == "=" and self._match(">"):
                self._add("ARROW", "=>", None, start_line, start_col)
                continue

            token_type = one_char_tokens.get(char)
            if token_type:
                self._add(token_type, char, None, start_line, start_col)
                continue

            raise _syntax_error(start_line, start_col, f"Bilinmeyen karakter: {char!r}", self.filename)

        self.tokens.append(Token("EOF", "", None, self.line, self.column))
        return self.tokens

    def _is_at_end(self) -> bool:
        return self.index >= self.length

    def _peek(self) -> str:
        if self._is_at_end():
            return ""
        return self.source[self.index]

    def _advance(self) -> str:
        char = self.source[self.index]
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _match(self, expected: str) -> bool:
        if self._is_at_end() or self.source[self.index] != expected:
            return False
        self._advance()
        return True

    def _add(self, token_type: str, lexeme: str, literal: Any, line: int, column: int) -> None:
        self.tokens.append(Token(token_type, lexeme, literal, line, column))

    def _number(self, first: str, line: int, column: int) -> None:
        chars = [first]
        has_dot = False

        while not self._is_at_end():
            char = self._peek()
            if char.isdigit():
                chars.append(self._advance())
                continue
            if char == "." and not has_dot and self.index + 1 < self.length and self.source[self.index + 1].isdigit():
                has_dot = True
                chars.append(self._advance())
                continue
            break

        lexeme = "".join(chars)
        literal = float(lexeme) if has_dot else int(lexeme)
        self._add("NUMBER", lexeme, literal, line, column)

    def _identifier(self, first: str, line: int, column: int) -> None:
        chars = [first]
        while not self._is_at_end() and self._is_identifier_part(self._peek()):
            chars.append(self._advance())

        lexeme = "".join(chars)
        lowered = lexeme.lower()
        token_type = KEYWORDS.get(lowered)
        if token_type == "BOOL":
            literal = lowered in {"dogru", "doğru"}
            self._add("BOOL", lexeme, literal, line, column)
        elif token_type == "NULL":
            self._add("NULL", lexeme, None, line, column)
        elif token_type:
            self._add(token_type, lexeme, lexeme, line, column)
        else:
            self._add("IDENT", lexeme, lexeme, line, column)

    def _string(self, quote: str, line: int, column: int) -> None:
        chars: List[str] = []
        escape = False

        while not self._is_at_end():
            char = self._advance()
            if escape:
                mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}
                chars.append(mapping.get(char, char))
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == quote:
                self._add("STRING", "".join(chars), "".join(chars), line, column)
                return
            chars.append(char)

        raise _syntax_error(line, column, "Metin kapanisi eksik", self.filename)

    @staticmethod
    def _is_identifier_start(char: str) -> bool:
        return char == "_" or char.isalpha()

    @staticmethod
    def _is_identifier_part(char: str) -> bool:
        return char == "_" or char.isalnum()


class Expr:
    pass


class Stmt:
    pass


@dataclass
class Parameter:
    name: str
    default: Optional[Expr]


@dataclass
class LiteralExpr(Expr):
    value: Any


@dataclass
class VariableExpr(Expr):
    name: str


@dataclass
class ListExpr(Expr):
    items: List[Expr]


@dataclass
class DictExpr(Expr):
    items: List[tuple[str, Expr]]


@dataclass
class UnaryExpr(Expr):
    operator: str
    right: Expr


@dataclass
class BinaryExpr(Expr):
    left: Expr
    operator: str
    right: Expr


@dataclass
class TernaryExpr(Expr):
    condition: Expr
    then_branch: Expr
    else_branch: Expr


@dataclass
class CallExpr(Expr):
    callee: Expr
    args: List[Expr]


@dataclass
class GetAttrExpr(Expr):
    obj: Expr
    name: str


@dataclass
class IndexExpr(Expr):
    obj: Expr
    index: Expr


@dataclass
class NewExpr(Expr):
    callee: Expr
    args: List[Expr]


@dataclass
class AnonymousFunctionExpr(Expr):
    params: List[Parameter]
    body: List["Stmt"]


@dataclass
class VarDecl(Stmt):
    name: str
    initializer: Optional[Expr]


@dataclass
class FunctionDecl(Stmt):
    name: str
    params: List[Parameter]
    body: List[Stmt]


@dataclass
class ClassDecl(Stmt):
    name: str
    fields: List[VarDecl]
    methods: List[FunctionDecl]


@dataclass
class BlockStmt(Stmt):
    statements: List[Stmt]


@dataclass
class IfStmt(Stmt):
    branches: List[tuple[Expr, List[Stmt]]]
    else_branch: Optional[List[Stmt]]


@dataclass
class WhileStmt(Stmt):
    condition: Expr
    body: List[Stmt]


@dataclass
class DoWhileStmt(Stmt):
    body: List[Stmt]
    condition: Expr


@dataclass
class ForStmt(Stmt):
    initializer: Optional[Stmt]
    condition: Optional[Expr]
    update: Optional[Stmt]
    body: List[Stmt]


@dataclass
class ForEachStmt(Stmt):
    name: str
    declare: bool
    iterable: Expr
    body: List[Stmt]


@dataclass
class SwitchCase:
    value: Expr
    statements: List[Stmt]


@dataclass
class SwitchStmt(Stmt):
    expression: Expr
    cases: List[SwitchCase]
    default: List[Stmt]


@dataclass
class TryCatchStmt(Stmt):
    try_block: List[Stmt]
    error_name: Optional[str]
    catch_block: List[Stmt]


@dataclass
class ThrowStmt(Stmt):
    expression: Expr


@dataclass
class ReturnStmt(Stmt):
    value: Optional[Expr]


@dataclass
class BreakStmt(Stmt):
    pass


@dataclass
class ContinueStmt(Stmt):
    pass


@dataclass
class ImportStmt(Stmt):
    path: Expr
    alias: Optional[str]


@dataclass
class AssignStmt(Stmt):
    target: Expr
    operator: str
    value: Expr


@dataclass
class UpdateStmt(Stmt):
    target: Expr
    delta: int


@dataclass
class ExpressionStmt(Stmt):
    expression: Expr


class Parser:
    def __init__(self, tokens: Sequence[Token], filename: str = "<girdi>"):
        self.tokens = list(tokens)
        self.index = 0
        self.filename = filename

    def parse(self) -> List[Stmt]:
        statements: List[Stmt] = []
        while not self._is_at_end():
            self._skip_semicolons()
            if self._is_at_end():
                break
            statements.append(self._statement())
        return statements

    def _statement(self) -> Stmt:
        if self._match("DEGISKEN"):
            return self._var_decl(require_end=True)
        if self._match("FONKSIYON"):
            return self._function_decl()
        if self._match("ITHAL"):
            return self._import_stmt()
        if self._match("SINIF"):
            return self._class_decl()
        if self._match("EGER"):
            return self._if_stmt()
        if self._match("DONGU"):
            return self._for_stmt()
        if self._match("HER"):
            return self._foreach_stmt()
        if self._match("WHILE"):
            return self._while_stmt()
        if self._match("YAP"):
            return self._do_while_stmt()
        if self._match("SEC"):
            return self._switch_stmt()
        if self._match("DENE"):
            return self._try_catch_stmt()
        if self._match("FIRLAT"):
            expr = self._expression()
            self._consume_statement_end()
            return ThrowStmt(expr)
        if self._match("DONDUR"):
            if self._check("SEMICOLON"):
                self._consume_statement_end()
                return ReturnStmt(None)
            expr = self._expression()
            self._consume_statement_end()
            return ReturnStmt(expr)
        if self._match("DEVAM"):
            self._consume_statement_end()
            return ContinueStmt()
        if self._match("BREAK"):
            self._consume_statement_end()
            return BreakStmt()
        if self._match("LBRACE"):
            return BlockStmt(self._block_statements())
        return self._expression_or_assignment_stmt()

    def _var_decl(self, require_end: bool) -> VarDecl:
        name = self._expect("IDENT", "Degisken adi bekleniyordu").literal
        initializer = None
        if self._match("EQUAL"):
            initializer = self._expression()
        if require_end:
            self._consume_statement_end()
        return VarDecl(name, initializer)

    def _function_decl(self) -> FunctionDecl:
        name = self._expect("IDENT", "Fonksiyon adi bekleniyordu").literal
        params = self._parameters()
        body = self._block()
        return FunctionDecl(name, params, body)

    def _import_stmt(self) -> ImportStmt:
        path = self._expression()
        alias = None
        if self._match("OLARAK"):
            alias = self._expect("IDENT", "Modul takma adi bekleniyordu").literal
        self._consume_statement_end()
        return ImportStmt(path, alias)

    def _class_decl(self) -> ClassDecl:
        name = self._expect("IDENT", "Sinif adi bekleniyordu").literal
        self._expect("LBRACE", "'{' bekleniyordu")
        fields: List[VarDecl] = []
        methods: List[FunctionDecl] = []

        while not self._check("RBRACE") and not self._is_at_end():
            self._skip_semicolons()
            if self._check("RBRACE"):
                break
            if self._match("DEGISKEN"):
                fields.append(self._var_decl(require_end=True))
                continue
            if self._match("FONKSIYON"):
                methods.append(self._function_decl())
                continue
            token = self._peek()
            raise _syntax_error(
                token.line,
                token.column,
                "Sinif govdesinde sadece degisken ve fonksiyon tanimlari destekleniyor",
                self.filename,
            )

        self._expect("RBRACE", "'}' bekleniyordu")
        return ClassDecl(name, fields, methods)

    def _parameters(self) -> List[Parameter]:
        self._expect("LPAREN", "'(' bekleniyordu")
        params: List[Parameter] = []
        if not self._check("RPAREN"):
            while True:
                name = self._expect("IDENT", "Parametre adi bekleniyordu").literal
                default = None
                if self._match("EQUAL"):
                    default = self._expression()
                params.append(Parameter(name, default))
                if not self._match("COMMA"):
                    break
        self._expect("RPAREN", "')' bekleniyordu")
        return params

    def _block(self) -> List[Stmt]:
        self._expect("LBRACE", "'{' bekleniyordu")
        return self._block_statements()

    def _block_statements(self) -> List[Stmt]:
        statements: List[Stmt] = []
        while not self._check("RBRACE") and not self._is_at_end():
            self._skip_semicolons()
            if self._check("RBRACE"):
                break
            statements.append(self._statement())
        self._expect("RBRACE", "'}' bekleniyordu")
        return statements

    def _if_stmt(self) -> IfStmt:
        self._expect("LPAREN", "'(' bekleniyordu")
        condition = self._expression()
        self._expect("RPAREN", "')' bekleniyordu")
        branches = [(condition, self._block())]
        else_branch: Optional[List[Stmt]] = None

        while self._match("DEGILSE"):
            if self._match("EGER"):
                self._expect("LPAREN", "'(' bekleniyordu")
                nested_condition = self._expression()
                self._expect("RPAREN", "')' bekleniyordu")
                branches.append((nested_condition, self._block()))
            else:
                else_branch = self._block()
                break

        return IfStmt(branches, else_branch)

    def _for_stmt(self) -> ForStmt:
        self._expect("LPAREN", "'(' bekleniyordu")
        initializer: Optional[Stmt] = None
        condition: Optional[Expr] = None
        update: Optional[Stmt] = None

        if not self._check("SEMICOLON"):
            initializer = self._for_header_stmt()
        self._expect("SEMICOLON", "';' bekleniyordu")

        if not self._check("SEMICOLON"):
            condition = self._expression()
        self._expect("SEMICOLON", "';' bekleniyordu")

        if not self._check("RPAREN"):
            update = self._for_header_stmt()
        self._expect("RPAREN", "')' bekleniyordu")
        body = self._block()
        return ForStmt(initializer, condition, update, body)

    def _foreach_stmt(self) -> ForEachStmt:
        self._expect("LPAREN", "'(' bekleniyordu")
        declare = self._match("DEGISKEN")
        name = self._expect("IDENT", "Dongu degiskeni bekleniyordu").literal
        self._expect("IN", "'in' bekleniyordu")
        iterable = self._expression()
        self._expect("RPAREN", "')' bekleniyordu")
        body = self._block()
        return ForEachStmt(name, declare, iterable, body)

    def _while_stmt(self) -> WhileStmt:
        self._expect("LPAREN", "'(' bekleniyordu")
        condition = self._expression()
        self._expect("RPAREN", "')' bekleniyordu")
        return WhileStmt(condition, self._block())

    def _do_while_stmt(self) -> DoWhileStmt:
        body = self._block()
        self._expect("WHILE", "'while' bekleniyordu")
        self._expect("LPAREN", "'(' bekleniyordu")
        condition = self._expression()
        self._expect("RPAREN", "')' bekleniyordu")
        if self._check("SEMICOLON"):
            self._advance()
        return DoWhileStmt(body, condition)

    def _switch_stmt(self) -> SwitchStmt:
        self._expect("LPAREN", "'(' bekleniyordu")
        expression = self._expression()
        self._expect("RPAREN", "')' bekleniyordu")
        self._expect("LBRACE", "'{' bekleniyordu")
        cases: List[SwitchCase] = []
        default: List[Stmt] = []

        while not self._check("RBRACE") and not self._is_at_end():
            self._skip_semicolons()
            if self._match("DURUM"):
                case_expr = self._expression()
                self._expect("COLON", "':' bekleniyordu")
                case_statements: List[Stmt] = []
                while not self._check("DURUM") and not self._check("VARSAYILAN") and not self._check("RBRACE"):
                    self._skip_semicolons()
                    if self._check("DURUM") or self._check("VARSAYILAN") or self._check("RBRACE"):
                        break
                    case_statements.append(self._statement())
                cases.append(SwitchCase(case_expr, case_statements))
                continue
            if self._match("VARSAYILAN"):
                self._expect("COLON", "':' bekleniyordu")
                while not self._check("RBRACE") and not self._is_at_end():
                    self._skip_semicolons()
                    if self._check("RBRACE"):
                        break
                    default.append(self._statement())
                break
            token = self._peek()
            raise _syntax_error(
                token.line,
                token.column,
                "Switch icinde 'durum' veya 'varsayilan' bekleniyordu",
                self.filename,
            )

        self._expect("RBRACE", "'}' bekleniyordu")
        return SwitchStmt(expression, cases, default)

    def _try_catch_stmt(self) -> TryCatchStmt:
        try_block = self._block()
        self._expect("YAKALA", "'yakala' bekleniyordu")
        error_name: Optional[str] = None
        if self._match("LPAREN"):
            error_name = self._expect("IDENT", "Hata degiskeni bekleniyordu").literal
            self._expect("RPAREN", "')' bekleniyordu")
        catch_block = self._block()
        return TryCatchStmt(try_block, error_name, catch_block)

    def _for_header_stmt(self) -> Stmt:
        if self._match("DEGISKEN"):
            return self._var_decl(require_end=False)

        expr = self._expression()
        if self._match("EQUAL", "PLUS_EQUAL", "MINUS_EQUAL", "STAR_EQUAL", "SLASH_EQUAL", "PERCENT_EQUAL"):
            operator = self._previous().type
            value = self._expression()
            return AssignStmt(expr, operator, value)
        if self._match("PLUS_PLUS"):
            return UpdateStmt(expr, 1)
        if self._match("MINUS_MINUS"):
            return UpdateStmt(expr, -1)
        return ExpressionStmt(expr)

    def _expression_or_assignment_stmt(self) -> Stmt:
        expr = self._expression()
        if self._match("EQUAL", "PLUS_EQUAL", "MINUS_EQUAL", "STAR_EQUAL", "SLASH_EQUAL", "PERCENT_EQUAL"):
            operator = self._previous().type
            value = self._expression()
            self._consume_statement_end()
            return AssignStmt(expr, operator, value)
        if self._match("PLUS_PLUS"):
            self._consume_statement_end()
            return UpdateStmt(expr, 1)
        if self._match("MINUS_MINUS"):
            self._consume_statement_end()
            return UpdateStmt(expr, -1)
        self._consume_statement_end()
        return ExpressionStmt(expr)

    def _expression(self) -> Expr:
        return self._ternary()

    def _ternary(self) -> Expr:
        expr = self._or()
        if self._match("QUESTION"):
            then_branch = self._expression()
            self._expect("COLON", "':' bekleniyordu")
            else_branch = self._expression()
            return TernaryExpr(expr, then_branch, else_branch)
        return expr

    def _or(self) -> Expr:
        expr = self._and()
        while self._match("VEYA"):
            operator = self._previous().type
            right = self._and()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _and(self) -> Expr:
        expr = self._equality()
        while self._match("VE"):
            operator = self._previous().type
            right = self._equality()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _equality(self) -> Expr:
        expr = self._comparison()
        while self._match("EQEQ", "BANGEQ"):
            operator = self._previous().type
            right = self._comparison()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _comparison(self) -> Expr:
        expr = self._term()
        while self._match("GT", "GTE", "LT", "LTE"):
            operator = self._previous().type
            right = self._term()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _term(self) -> Expr:
        expr = self._factor()
        while self._match("PLUS", "MINUS"):
            operator = self._previous().type
            right = self._factor()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _factor(self) -> Expr:
        expr = self._power()
        while self._match("STAR", "SLASH", "PERCENT"):
            operator = self._previous().type
            right = self._power()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _power(self) -> Expr:
        expr = self._unary()
        if self._match("CARET"):
            operator = self._previous().type
            right = self._power()
            return BinaryExpr(expr, operator, right)
        return expr

    def _unary(self) -> Expr:
        if self._match("MINUS"):
            return UnaryExpr("NEGATE", self._unary())
        if self._match("PLUS"):
            return UnaryExpr("POSITIVE", self._unary())
        if self._match("BANG", "DEGIL"):
            return UnaryExpr("NOT", self._unary())
        if self._match("YENI"):
            target = self._call()
            if isinstance(target, CallExpr):
                return NewExpr(target.callee, target.args)
            return NewExpr(target, [])
        return self._call()

    def _call(self) -> Expr:
        expr = self._primary()
        while True:
            if self._match("LPAREN"):
                args: List[Expr] = []
                if not self._check("RPAREN"):
                    while True:
                        args.append(self._expression())
                        if not self._match("COMMA"):
                            break
                self._expect("RPAREN", "')' bekleniyordu")
                expr = CallExpr(expr, args)
                continue
            if self._match("DOT"):
                if self._peek().type not in PROPERTY_NAME_TOKENS:
                    token = self._peek()
                    raise _syntax_error(token.line, token.column, "Ozellik adi bekleniyordu", self.filename)
                name = self._advance().literal
                expr = GetAttrExpr(expr, name)
                continue
            if self._match("LBRACKET"):
                index = self._expression()
                self._expect("RBRACKET", "']' bekleniyordu")
                expr = IndexExpr(expr, index)
                continue
            break
        return expr

    def _primary(self) -> Expr:
        lambda_expr = self._try_arrow_function()
        if lambda_expr is not None:
            return lambda_expr
        if self._check("IDENT") and self._peek_ahead(1).type == "ARROW":
            param_name = self._advance().literal
            self._advance()
            return AnonymousFunctionExpr([Parameter(param_name, None)], self._lambda_body())
        if self._match("FONKSIYON"):
            return self._anonymous_function_expression()
        if self._match("NUMBER", "STRING", "BOOL", "NULL"):
            return LiteralExpr(self._previous().literal)
        if self._match("IDENT"):
            return VariableExpr(self._previous().literal)
        if self._match("THIS"):
            return VariableExpr("this")
        if self._match("LPAREN"):
            expr = self._expression()
            self._expect("RPAREN", "')' bekleniyordu")
            return expr
        if self._match("LBRACKET"):
            items: List[Expr] = []
            if not self._check("RBRACKET"):
                while True:
                    items.append(self._expression())
                    if self._match("COMMA", "SEMICOLON"):
                        if self._check("RBRACKET"):
                            break
                        continue
                    else:
                        break
            self._expect("RBRACKET", "']' bekleniyordu")
            return ListExpr(items)
        if self._match("LBRACE"):
            items: List[tuple[str, Expr]] = []
            if not self._check("RBRACE"):
                while True:
                    key_token = self._expect_any(("IDENT", "STRING"), "Nesne anahtari bekleniyordu")
                    self._expect("COLON", "':' bekleniyordu")
                    value = self._expression()
                    items.append((str(key_token.literal), value))
                    if self._match("COMMA", "SEMICOLON"):
                        if self._check("RBRACE"):
                            break
                        continue
                    else:
                        break
            self._expect("RBRACE", "'}' bekleniyordu")
            return DictExpr(items)

        token = self._peek()
        raise _syntax_error(token.line, token.column, "Ifade bekleniyordu", self.filename)

    def _anonymous_function_expression(self) -> AnonymousFunctionExpr:
        params = self._parameters()
        body = self._block()
        return AnonymousFunctionExpr(params, body)

    def _try_arrow_function(self) -> Optional[AnonymousFunctionExpr]:
        if not self._check("LPAREN"):
            return None

        start = self.index
        try:
            self._advance()
            params: List[Parameter] = []
            if not self._check("RPAREN"):
                while True:
                    name = self._expect("IDENT", "Parametre adi bekleniyordu").literal
                    default = None
                    if self._match("EQUAL"):
                        default = self._expression()
                    params.append(Parameter(name, default))
                    if not self._match("COMMA"):
                        break
            self._expect("RPAREN", "')' bekleniyordu")
            if not self._match("ARROW"):
                self.index = start
                return None
            return AnonymousFunctionExpr(params, self._lambda_body())
        except TurkCodeSyntaxError:
            self.index = start
            return None

    def _lambda_body(self) -> List[Stmt]:
        if self._check("LBRACE"):
            return self._block()
        return [ReturnStmt(self._expression())]

    def _skip_semicolons(self) -> None:
        while self._match("SEMICOLON"):
            pass

    def _consume_statement_end(self) -> None:
        if self._match("SEMICOLON"):
            self._skip_semicolons()
            return
        token = self._peek()
        raise _syntax_error(token.line, token.column, "';' bekleniyordu", self.filename)

    def _expect(self, token_type: str, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        token = self._peek()
        raise _syntax_error(token.line, token.column, message, self.filename)

    def _expect_any(self, token_types: Sequence[str], message: str) -> Token:
        for token_type in token_types:
            if self._check(token_type):
                return self._advance()
        token = self._peek()
        raise _syntax_error(token.line, token.column, message, self.filename)

    def _match(self, *token_types: str) -> bool:
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _check(self, token_type: str) -> bool:
        if self._is_at_end():
            return token_type == "EOF"
        return self._peek().type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.index += 1
        return self.tokens[self.index - 1]

    def _peek(self) -> Token:
        return self.tokens[self.index]

    def _peek_ahead(self, distance: int) -> Token:
        target = self.index + distance
        if target >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[target]

    def _previous(self) -> Token:
        return self.tokens[self.index - 1]

    def _is_at_end(self) -> bool:
        return self._peek().type == "EOF"


class ReturnSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class RaisedSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


class Environment:
    def __init__(self, parent: Optional["Environment"] = None):
        self.parent = parent
        self.values: Dict[str, Any] = {}

    def define(self, name: str, value: Any) -> Any:
        self.values[name] = value
        return value

    def contains_here(self, name: str) -> bool:
        return name in self.values

    def contains(self, name: str) -> bool:
        if name in self.values:
            return True
        if self.parent is not None:
            return self.parent.contains(name)
        return False

    def assign(self, name: str, value: Any) -> Any:
        if name in self.values:
            self.values[name] = value
            return value
        if self.parent is not None:
            return self.parent.assign(name, value)
        raise TurkCodeRuntimeError(f"Tanimlanmamis degisken: {name}")

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise TurkCodeRuntimeError(f"Tanimlanmamis degisken: {name}")


class MemberObject:
    def get_member(self, name: str) -> Any:
        raise NotImplementedError

    def set_member(self, name: str, value: Any) -> Any:
        raise NotImplementedError


class TurkMap(MemberObject):
    def __init__(self, items: Optional[Dict[str, Any]] = None):
        self.data: Dict[str, Any] = dict(items or {})

    def get_member(self, name: str) -> Any:
        if name in self.data:
            return self.data[name]
        raise TurkCodeRuntimeError(f"Nesne ozelligi bulunamadi: {name}")

    def set_member(self, name: str, value: Any) -> Any:
        self.data[name] = value
        return value

    def __getitem__(self, key: Any) -> Any:
        return self.data[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self.data[key] = value

    def __contains__(self, key: Any) -> bool:
        return key in self.data

    def items(self):
        return self.data.items()

    def keys(self):
        return self.data.keys()

    def __len__(self) -> int:
        return len(self.data)


class CallableValue:
    def call(self, interpreter: "TurkCodeInterpreter", args: List[Any]) -> Any:
        raise NotImplementedError


class BuiltinFunction(CallableValue):
    def __init__(self, name: str, func: Callable[..., Any]):
        self.name = name
        self.func = func

    def call(self, interpreter: "TurkCodeInterpreter", args: List[Any]) -> Any:
        try:
            raw_args = [unwrap_value(arg) for arg in args]
            return wrap_value(self.func(*raw_args))
        except TurkCodeError:
            raise
        except TypeError as exc:
            raise TurkCodeRuntimeError(f"{self.name} cagrisi gecersiz: {exc}") from exc
        except Exception as exc:
            raise TurkCodeRuntimeError(f"{self.name} cagrisi basarisiz: {exc}") from exc

    def __repr__(self) -> str:
        return f"<yerlesik fonksiyon {self.name}>"


class UserFunction(CallableValue):
    def __init__(self, declaration: FunctionDecl, closure: Environment):
        self.declaration = declaration
        self.closure = closure

    @property
    def name(self) -> str:
        return self.declaration.name

    def bind(self, instance: "TurkInstance") -> "BoundMethod":
        return BoundMethod(instance, self)

    def call(self, interpreter: "TurkCodeInterpreter", args: List[Any]) -> Any:
        return self._invoke(interpreter, args, None)

    def _invoke(self, interpreter: "TurkCodeInterpreter", args: List[Any], instance: Optional["TurkInstance"]) -> Any:
        local = Environment(self.closure)
        if instance is not None:
            local.define("this", instance)

        for index, param in enumerate(self.declaration.params):
            if index < len(args):
                local.define(param.name, args[index])
            elif param.default is not None:
                local.define(param.name, interpreter.evaluate(param.default, local))
            else:
                raise TurkCodeRuntimeError(f"Eksik parametre: {param.name}")

        try:
            interpreter.execute_block(self.declaration.body, local)
        except ReturnSignal as signal:
            return signal.value
        return None

    def __repr__(self) -> str:
        return f"<fonksiyon {self.name}>"


class BoundMethod(CallableValue):
    def __init__(self, instance: "TurkInstance", function: UserFunction):
        self.instance = instance
        self.function = function

    def call(self, interpreter: "TurkCodeInterpreter", args: List[Any]) -> Any:
        return self.function._invoke(interpreter, args, self.instance)

    def __repr__(self) -> str:
        return f"<bagli metod {self.function.name}>"


class UserClass(CallableValue):
    def __init__(self, name: str, fields: List[VarDecl], methods: Dict[str, UserFunction], closure: Environment):
        self.name = name
        self.fields = fields
        self.methods = methods
        self.closure = closure

    def find_method(self, name: str) -> Optional[UserFunction]:
        return self.methods.get(name)

    def call(self, interpreter: "TurkCodeInterpreter", args: List[Any]) -> Any:
        instance = TurkInstance(self)
        field_env = Environment(self.closure)
        field_env.define("this", instance)
        for field in self.fields:
            value = None if field.initializer is None else interpreter.evaluate(field.initializer, field_env)
            instance.set_member(field.name, value)

        initializer = self.find_method("baslat")
        if initializer is not None:
            initializer._invoke(interpreter, args, instance)
        elif args:
            raise TurkCodeRuntimeError(f"{self.name} yapicisi parametre almiyor")
        return instance

    def __repr__(self) -> str:
        return f"<sinif {self.name}>"


class TurkInstance(MemberObject):
    def __init__(self, klass: UserClass):
        self.klass = klass
        self.fields: Dict[str, Any] = {}

    def get_member(self, name: str) -> Any:
        if name in self.fields:
            return self.fields[name]
        method = self.klass.find_method(name)
        if method is not None:
            return method.bind(self)
        raise TurkCodeRuntimeError(f"{self.klass.name} icinde '{name}' bulunamadi")

    def set_member(self, name: str, value: Any) -> Any:
        self.fields[name] = value
        return value

    def __repr__(self) -> str:
        return f"<{self.klass.name} nesnesi>"


class TurkModule(MemberObject):
    def __init__(self, name: str):
        self.name = name
        self.members: Dict[str, Any] = {}

    def register(self, names: Iterable[str], value: Any) -> None:
        for name in names:
            self.members[name] = value

    def get_member(self, name: str) -> Any:
        if name in self.members:
            return self.members[name]
        raise TurkCodeRuntimeError(f"{self.name} modulu icinde '{name}' bulunamadi")

    def set_member(self, name: str, value: Any) -> Any:
        self.members[name] = value
        return value

    def __repr__(self) -> str:
        return f"<modul {self.name}>"


class PythonModule(TurkModule):
    def __init__(self, module: types.ModuleType, display_name: Optional[str] = None):
        super().__init__(display_name or module.__name__)
        self.module = module
        self.members = self._collect_public_members()

    def _collect_public_members(self) -> Dict[str, Any]:
        members: Dict[str, Any] = {}
        try:
            public_names = list(getattr(self.module, "__all__", None) or dir(self.module))
        except Exception:
            public_names = []

        for actual_name in public_names:
            if not isinstance(actual_name, str) or actual_name.startswith("_"):
                continue
            try:
                value = getattr(self.module, actual_name)
            except Exception:
                continue
            members.setdefault(actual_name, wrap_value(value))
            for alias in _python_alias_candidates(actual_name):
                members.setdefault(alias, wrap_value(value))
        return members

    def get_member(self, name: str) -> Any:
        actual_name = _resolve_python_member_name(self.module, name)
        if actual_name is not None:
            try:
                return wrap_value(getattr(self.module, actual_name))
            except Exception as exc:
                raise TurkCodeRuntimeError(f"{self.name}.{name} okunamadi: {exc}") from exc
        raise TurkCodeRuntimeError(f"{self.name} kutuphanesi icinde '{name}' bulunamadi")

    def set_member(self, name: str, value: Any) -> Any:
        setattr(self.module, name, unwrap_value(value))
        self.members[name] = value
        return value

    def __repr__(self) -> str:
        return f"<python kutuphanesi {self.module.__name__}>"


def wrap_value(value: Any) -> Any:
    if isinstance(value, (TurkMap, UserClass, UserFunction, BuiltinFunction, BoundMethod, TurkModule, TurkInstance)):
        return value
    if isinstance(value, types.ModuleType):
        return PythonModule(value)
    if isinstance(value, dict):
        return TurkMap({str(key): wrap_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return [wrap_value(item) for item in value]
    if isinstance(value, tuple):
        return [wrap_value(item) for item in value]
    return value


def unwrap_value(value: Any) -> Any:
    if isinstance(value, TurkMap):
        return {key: unwrap_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [unwrap_value(item) for item in value]
    if isinstance(value, TurkInstance):
        return {key: unwrap_value(item) for key, item in value.fields.items()}
    return value


def stringify(value: Any, nested: bool = False) -> str:
    value = wrap_value(value)
    if value is None:
        return "bos"
    if value is True:
        return "dogru"
    if value is False:
        return "yanlis"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False) if nested else value
    if isinstance(value, list):
        return "[" + ", ".join(stringify(item, nested=True) for item in value) + "]"
    if isinstance(value, TurkMap):
        parts = []
        for key, item in value.items():
            pretty_key = key if re.match(r"^[A-Za-z_ÇĞİÖŞÜçğıöşü][A-Za-z0-9_ÇĞİÖŞÜçğıöşü]*$", key) else json.dumps(key, ensure_ascii=False)
            parts.append(f"{pretty_key}: {stringify(item, nested=True)}")
        return "{" + ", ".join(parts) + "}"
    if isinstance(value, CallableValue):
        return repr(value)
    return str(value)


def get_member(obj: Any, name: str) -> Any:
    obj = wrap_value(obj)
    if isinstance(obj, MemberObject):
        return obj.get_member(name)
    if isinstance(obj, dict):
        if name in obj:
            return wrap_value(obj[name])
    actual_name = _resolve_python_member_name(obj, name)
    if actual_name is not None:
        try:
            return wrap_value(getattr(obj, actual_name))
        except Exception as exc:
            raise TurkCodeRuntimeError(f"'{type(obj).__name__}' icinde '{name}' okunamadi: {exc}") from exc
    raise TurkCodeRuntimeError(f"'{type(obj).__name__}' tipinde '{name}' ozelligi yok")


def set_member(obj: Any, name: str, value: Any) -> Any:
    obj = wrap_value(obj)
    if isinstance(obj, MemberObject):
        return obj.set_member(name, value)
    if isinstance(obj, dict):
        obj[name] = value
        return value
    if hasattr(obj, "__dict__"):
        actual_name = _resolve_python_member_name(obj, name) or name
        setattr(obj, actual_name, unwrap_value(value))
        return value
    raise TurkCodeRuntimeError(f"'{type(obj).__name__}' tipine ozellik atanamiyor")


def get_index(obj: Any, index: Any) -> Any:
    obj = wrap_value(obj)
    index = unwrap_value(index)
    if isinstance(obj, TurkMap):
        if str(index) in obj.data:
            return obj.data[str(index)]
        raise TurkCodeRuntimeError(f"Nesne anahtari bulunamadi: {index}")
    try:
        return wrap_value(obj[index])
    except Exception as exc:
        raise TurkCodeRuntimeError(f"Indeks erisimi basarisiz: {exc}") from exc


def set_index(obj: Any, index: Any, value: Any) -> Any:
    obj = wrap_value(obj)
    index = unwrap_value(index)
    if isinstance(obj, TurkMap):
        obj.data[str(index)] = value
        return value
    try:
        obj[index] = value
        return value
    except Exception as exc:
        raise TurkCodeRuntimeError(f"Indeks atamasi basarisiz: {exc}") from exc


class FileModule(TurkModule):
    def __init__(self):
        super().__init__("dosya")
        self.register(("oku",), BuiltinFunction("dosya.oku", self.read_text))
        self.register(("satirlariOku", "satırlarıOku"), BuiltinFunction("dosya.satirlariOku", self.read_lines))
        self.register(("yaz",), BuiltinFunction("dosya.yaz", self.write_text))
        self.register(("ekle",), BuiltinFunction("dosya.ekle", self.append_text))
        self.register(("varMi", "varMı"), BuiltinFunction("dosya.varMi", self.exists))
        self.register(("klasorMu", "klasörMü"), BuiltinFunction("dosya.klasorMu", self.is_dir))

    @staticmethod
    def read_text(path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    @staticmethod
    def read_lines(path: str) -> List[str]:
        return Path(path).read_text(encoding="utf-8").splitlines()

    @staticmethod
    def write_text(path: str, content: Any) -> str:
        Path(path).write_text(str(content), encoding="utf-8")
        return "basarili"

    @staticmethod
    def append_text(path: str, content: Any) -> str:
        with Path(path).open("a", encoding="utf-8") as handle:
            handle.write(str(content))
        return "basarili"

    @staticmethod
    def exists(path: str) -> bool:
        return Path(path).exists()

    @staticmethod
    def is_dir(path: str) -> bool:
        return Path(path).is_dir()


class NetworkModule(TurkModule):
    def __init__(self):
        super().__init__("ag")
        self.register(("iste",), BuiltinFunction("ag.iste", self.request))

    @staticmethod
    def request(method: str, url: str) -> Dict[str, Any]:
        return {
            "metod": method.upper(),
            "url": url,
            "durum": 200,
            "govde": "",
            "basliklar": {},
        }


class DateModule(TurkModule):
    def __init__(self):
        super().__init__("tarih")
        self.register(("simdi",), BuiltinFunction("tarih.simdi", lambda: dt.datetime.now().isoformat()))
        self.register(("bugun",), BuiltinFunction("tarih.bugun", lambda: dt.date.today().isoformat()))
        self.register(("formatla",), BuiltinFunction("tarih.formatla", self.format_date))

    @staticmethod
    def format_date(value: Any, pattern: str) -> str:
        if isinstance(value, str):
            try:
                parsed = dt.datetime.fromisoformat(value)
            except ValueError:
                parsed = dt.datetime.combine(dt.date.fromisoformat(value), dt.time())
            value = parsed
        return value.strftime(pattern)


class JsonModule(TurkModule):
    def __init__(self):
        super().__init__("json")
        self.register(("donustur", "dönüştür"), BuiltinFunction("json.donustur", self.encode))
        self.register(("coz", "çöz"), BuiltinFunction("json.coz", self.decode))

    @staticmethod
    def encode(value: Any) -> str:
        return json.dumps(unwrap_value(value), ensure_ascii=False)

    @staticmethod
    def decode(text: str) -> Any:
        return wrap_value(json.loads(text))


class RegexModule(TurkModule):
    def __init__(self):
        super().__init__("regex")
        self.register(("esles", "eşleş"), BuiltinFunction("regex.esles", self.search))
        self.register(("bul",), BuiltinFunction("regex.bul", self.findall))
        self.register(("degistir", "değiştir"), BuiltinFunction("regex.degistir", self.replace))

    @staticmethod
    def search(pattern: str, text: str) -> Any:
        match = re.search(pattern, text)
        if not match:
            return None
        return {"tamamı": match.group(0), "gruplar": list(match.groups())}

    @staticmethod
    def findall(pattern: str, text: str) -> List[Any]:
        return re.findall(pattern, text)

    @staticmethod
    def replace(pattern: str, repl: str, text: str) -> str:
        return re.sub(pattern, repl, text)


class TurkCodeInterpreter:
    def __init__(self, workspace_root: Optional[str] = None):
        self.globals = Environment()
        self.degiskenler = self.globals.values
        self.fonksiyonlar: Dict[str, Any] = {}
        self.siniflar: Dict[str, Any] = {}
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self.import_cache: Dict[str, TurkModule] = {}
        self._source_stack: List[Optional[Path]] = []
        self._import_stack: List[str] = []
        self.modules = {
            "dosya": FileModule(),
            "ag": NetworkModule(),
            "tarih": DateModule(),
            "json": JsonModule(),
            "regex": RegexModule(),
        }
        self._register_builtins()

    def _register_builtin(self, names: Iterable[str], func: Callable[..., Any]) -> None:
        first = next(iter(tuple(names)))
        builtin = BuiltinFunction(first, func)
        for name in names:
            self.globals.define(name, builtin)
            self.fonksiyonlar[name] = builtin

    def _register_module_factory(self, names: Iterable[str], module: TurkModule) -> None:
        self._register_builtin(names, lambda module=module: module)

    def _register_builtins(self) -> None:
        self._register_builtin(("yaz",), self._builtin_print)
        self._register_builtin(("girinti",), self._builtin_input)
        self._register_builtin(
            ("kutuphane", "kütüphane", "modul", "modül", "paket", "pythonKutuphane", "pythonKütüphane"),
            self._builtin_library,
        )

        self._register_builtin(("uzunluk",), lambda value: len(unwrap_value(value)))
        self._register_builtin(("ilk",), lambda value: unwrap_value(value)[0] if unwrap_value(value) else None)
        self._register_builtin(("son",), lambda value: unwrap_value(value)[-1] if unwrap_value(value) else None)
        self._register_builtin(("sirala", "sırala"), lambda value: sorted(unwrap_value(value)))
        self._register_builtin(("ters",), lambda value: list(reversed(unwrap_value(value))))
        self._register_builtin(("ekle",), lambda value, item: list(unwrap_value(value)) + [unwrap_value(item)])
        self._register_builtin(("harita",), lambda func, values: self._map_values(func, values))
        self._register_builtin(("suz", "süz"), lambda func, values: self._filter_values(func, values))
        self._register_builtin(("azalt",), lambda func, values, initial=None: self._reduce_values(func, values, initial))
        self._register_builtin(("aralik", "aralık"), self._range_values)
        self._register_builtin(("sil",), self._list_remove)
        self._register_builtin(("dilim",), self._slice)
        self._register_builtin(("birlestir", "birleştir"), self._join_or_concat)

        self._register_builtin(("buyukHarf", "büyükHarf"), lambda text: str(text).upper())
        self._register_builtin(("kucukHarf", "küçükHarf"), lambda text: str(text).lower())
        self._register_builtin(("degistir", "değiştir"), lambda text, old, new: str(text).replace(str(old), str(new)))
        self._register_builtin(("icerir", "içerir"), lambda text, needle: str(needle) in str(text))
        self._register_builtin(("basla", "başla"), lambda text, prefix: str(text).startswith(str(prefix)))
        self._register_builtin(("bitir",), lambda text, suffix: str(text).endswith(str(suffix)))
        self._register_builtin(("parcala", "parçala"), lambda text, delim=" ": str(text).split(str(delim)))
        self._register_builtin(("karakter",), lambda text, index: str(text)[int(index)])
        self._register_builtin(("metinParcasi", "metinParçası"), self._substring)

        self._register_builtin(("yuvarla",), lambda value: round(float(value)))
        self._register_builtin(("yuvarlaAsagi", "yuvarlaAşağı"), lambda value: math.floor(float(value)))
        self._register_builtin(("yuvarlaYukari", "yuvarlaYukarı"), lambda value: math.ceil(float(value)))
        self._register_builtin(("mutlak",), lambda value: abs(value))
        self._register_builtin(("karekok", "karekök"), lambda value: math.sqrt(float(value)))
        self._register_builtin(("us", "üs"), lambda a, b: a ** b)
        self._register_builtin(("tamBol",), lambda a, b: int(a) // int(b))
        self._register_builtin(("sin",), lambda value: math.sin(float(value)))
        self._register_builtin(("cos",), lambda value: math.cos(float(value)))
        self._register_builtin(("tan",), lambda value: math.tan(float(value)))
        self._register_builtin(("log",), lambda value: math.log(float(value)))
        self._register_builtin(("log10",), lambda value: math.log10(float(value)))
        self._register_builtin(("rastgele",), lambda: random.random())
        self._register_builtin(("rastgeleTam",), lambda a=0, b=100: random.randint(int(a), int(b)))

        self._register_builtin(("simdi", "şimdi"), lambda: dt.datetime.now().isoformat())
        self._register_builtin(("tarih",), lambda: dt.date.today().isoformat())
        self._register_builtin(("saat",), lambda: dt.datetime.now().strftime("%H:%M:%S"))
        self._register_builtin(("zaman",), lambda: int(dt.datetime.now().timestamp()))

        self._register_builtin(("tam",), lambda value=0: int(value if value is not None else 0))
        self._register_builtin(("ondalik", "ondalık"), lambda value=0: float(value if value is not None else 0))
        self._register_builtin(("metin",), lambda value="": stringify(value))

        self._register_builtin(("tip",), self._type_name)
        self._register_builtin(("miSayi",), lambda value: isinstance(value, (int, float)) and not isinstance(value, bool))
        self._register_builtin(("miMetin",), lambda value: isinstance(value, str))
        self._register_builtin(("miListe",), lambda value: isinstance(value, list))
        self._register_builtin(("miNesne",), lambda value: isinstance(wrap_value(value), TurkMap))

        self._register_module_factory(("dosya",), self.modules["dosya"])
        self._register_module_factory(("ag", "ağ"), self.modules["ag"])
        self._register_module_factory(("tarihModul", "tarihModülü"), self.modules["tarih"])
        self._register_module_factory(("json",), self.modules["json"])
        self._register_module_factory(("regex",), self.modules["regex"])

    def tamamlama_sozcukleri(self) -> List[str]:
        words = set(KEYWORDS.keys())
        words.update(self.fonksiyonlar.keys())
        words.update(self.modules.keys())
        words.update(PYTHON_MODULE_ALIASES.keys())
        for aliases in PYTHON_MEMBER_ALIASES.values():
            words.update(aliases)
        words.update({"this", "yeni"})
        return sorted(words)

    def cozumle(self, kod: str, dosya_adi: str = "<girdi>") -> List[Stmt]:
        normalized = normalize_source(kod)
        tokens = Lexer(normalized, dosya_adi).tokenize()
        return Parser(tokens, dosya_adi).parse()

    def calistir(
        self,
        kod: str,
        dosya_adi: str = "<girdi>",
        env: Optional[Environment] = None,
    ) -> Any:
        statements = self.cozumle(kod, dosya_adi)
        result = None
        target_env = self.globals if env is None else env
        source_path = None
        if dosya_adi and dosya_adi != "<girdi>":
            try:
                source_path = Path(dosya_adi).resolve()
            except OSError:
                source_path = None
        self._source_stack.append(source_path)
        try:
            for statement in statements:
                result = self.execute(statement, target_env)
        finally:
            self._source_stack.pop()
        return result

    def calistir_dosya(self, yol: str, env: Optional[Environment] = None) -> Any:
        path = Path(yol).resolve()
        return self.calistir(path.read_text(encoding="utf-8"), dosya_adi=str(path), env=env)

    def execute_block(self, statements: Sequence[Stmt], env: Environment) -> Any:
        result = None
        for statement in statements:
            result = self.execute(statement, env)
        return result

    def execute(self, statement: Stmt, env: Environment) -> Any:
        if isinstance(statement, VarDecl):
            value = None if statement.initializer is None else self.evaluate(statement.initializer, env)
            env.define(statement.name, value)
            if env is self.globals:
                self.degiskenler[statement.name] = value
            return value

        if isinstance(statement, ImportStmt):
            return self._execute_import(statement, env)

        if isinstance(statement, FunctionDecl):
            function = UserFunction(statement, env)
            env.define(statement.name, function)
            self.fonksiyonlar[statement.name] = function
            return function

        if isinstance(statement, ClassDecl):
            method_map = {method.name: UserFunction(method, env) for method in statement.methods}
            klass = UserClass(statement.name, statement.fields, method_map, env)
            env.define(statement.name, klass)
            self.siniflar[statement.name] = klass
            return klass

        if isinstance(statement, BlockStmt):
            return self.execute_block(statement.statements, env)

        if isinstance(statement, IfStmt):
            for condition, branch in statement.branches:
                if self._truthy(self.evaluate(condition, env)):
                    return self.execute_block(branch, env)
            if statement.else_branch is not None:
                return self.execute_block(statement.else_branch, env)
            return None

        if isinstance(statement, WhileStmt):
            result = None
            while self._truthy(self.evaluate(statement.condition, env)):
                try:
                    result = self.execute_block(statement.body, env)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            return result

        if isinstance(statement, DoWhileStmt):
            result = None
            while True:
                try:
                    result = self.execute_block(statement.body, env)
                except ContinueSignal:
                    pass
                except BreakSignal:
                    break
                if not self._truthy(self.evaluate(statement.condition, env)):
                    break
            return result

        if isinstance(statement, ForStmt):
            result = None
            if statement.initializer is not None:
                self.execute(statement.initializer, env)
            while True:
                if statement.condition is not None and not self._truthy(self.evaluate(statement.condition, env)):
                    break
                try:
                    result = self.execute_block(statement.body, env)
                except ContinueSignal:
                    pass
                except BreakSignal:
                    break
                if statement.update is not None:
                    self.execute(statement.update, env)
            return result

        if isinstance(statement, ForEachStmt):
            iterable = wrap_value(self.evaluate(statement.iterable, env))
            if isinstance(iterable, TurkMap):
                values = list(iterable.keys())
            else:
                try:
                    values = list(iterable)
                except TypeError as exc:
                    raise TurkCodeRuntimeError(f"Tekrarlanabilir degil: {iterable}") from exc

            result = None
            for item in values:
                value = wrap_value(item)
                if statement.declare and not env.contains_here(statement.name):
                    env.define(statement.name, value)
                elif statement.declare and env.contains_here(statement.name):
                    env.assign(statement.name, value)
                elif env.contains_here(statement.name) or env.parent is not None:
                    try:
                        env.assign(statement.name, value)
                    except TurkCodeRuntimeError:
                        env.define(statement.name, value)
                else:
                    env.define(statement.name, value)
                try:
                    result = self.execute_block(statement.body, env)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
            return result

        if isinstance(statement, SwitchStmt):
            switch_value = self.evaluate(statement.expression, env)
            matched = False
            result = None
            try:
                for case in statement.cases:
                    case_value = self.evaluate(case.value, env)
                    if matched or switch_value == case_value:
                        matched = True
                        result = self.execute_block(case.statements, env)
                if not matched and statement.default:
                    result = self.execute_block(statement.default, env)
            except BreakSignal:
                return result
            return result

        if isinstance(statement, TryCatchStmt):
            try:
                return self.execute_block(statement.try_block, env)
            except RaisedSignal as signal:
                return self._handle_catch(statement, signal.value, env)
            except TurkCodeRuntimeError as signal:
                return self._handle_catch(statement, str(signal), env)
            except Exception as signal:
                return self._handle_catch(statement, str(signal), env)

        if isinstance(statement, ThrowStmt):
            raise RaisedSignal(self.evaluate(statement.expression, env))

        if isinstance(statement, ReturnStmt):
            value = None if statement.value is None else self.evaluate(statement.value, env)
            raise ReturnSignal(value)

        if isinstance(statement, BreakStmt):
            raise BreakSignal()

        if isinstance(statement, ContinueStmt):
            raise ContinueSignal()

        if isinstance(statement, AssignStmt):
            return self._assign(statement.target, statement.operator, statement.value, env)

        if isinstance(statement, UpdateStmt):
            operator = "PLUS_EQUAL" if statement.delta > 0 else "MINUS_EQUAL"
            return self._assign(statement.target, operator, LiteralExpr(abs(statement.delta)), env)

        if isinstance(statement, ExpressionStmt):
            return self.evaluate(statement.expression, env)

        raise TurkCodeRuntimeError(f"Bilinmeyen ifade tipi: {type(statement).__name__}")

    def evaluate(self, expression: Expr, env: Environment) -> Any:
        if isinstance(expression, LiteralExpr):
            return wrap_value(expression.value)

        if isinstance(expression, VariableExpr):
            return env.get(expression.name)

        if isinstance(expression, AnonymousFunctionExpr):
            declaration = FunctionDecl("<anon>", expression.params, expression.body)
            return UserFunction(declaration, env)

        if isinstance(expression, ListExpr):
            return [self.evaluate(item, env) for item in expression.items]

        if isinstance(expression, DictExpr):
            return TurkMap({key: self.evaluate(value, env) for key, value in expression.items})

        if isinstance(expression, UnaryExpr):
            right = self.evaluate(expression.right, env)
            if expression.operator == "NEGATE":
                return -right
            if expression.operator == "POSITIVE":
                return +right
            if expression.operator == "NOT":
                return not self._truthy(right)
            raise TurkCodeRuntimeError(f"Gecersiz tekli operator: {expression.operator}")

        if isinstance(expression, BinaryExpr):
            if expression.operator == "VEYA":
                left = self.evaluate(expression.left, env)
                return left if self._truthy(left) else self.evaluate(expression.right, env)
            if expression.operator == "VE":
                left = self.evaluate(expression.left, env)
                return self.evaluate(expression.right, env) if self._truthy(left) else left

            left = self.evaluate(expression.left, env)
            right = self.evaluate(expression.right, env)

            if expression.operator == "PLUS":
                if isinstance(left, str) or isinstance(right, str):
                    return stringify(left) + stringify(right)
                try:
                    return left + right
                except Exception as exc:
                    raise TurkCodeRuntimeError(f"Toplama yapilamadi: {exc}") from exc
            if expression.operator == "MINUS":
                return left - right
            if expression.operator == "STAR":
                return left * right
            if expression.operator == "SLASH":
                return left / right
            if expression.operator == "PERCENT":
                return left % right
            if expression.operator == "CARET":
                return left ** right
            if expression.operator == "EQEQ":
                return left == right
            if expression.operator == "BANGEQ":
                return left != right
            if expression.operator == "GT":
                return left > right
            if expression.operator == "GTE":
                return left >= right
            if expression.operator == "LT":
                return left < right
            if expression.operator == "LTE":
                return left <= right
            raise TurkCodeRuntimeError(f"Gecersiz ikili operator: {expression.operator}")

        if isinstance(expression, TernaryExpr):
            if self._truthy(self.evaluate(expression.condition, env)):
                return self.evaluate(expression.then_branch, env)
            return self.evaluate(expression.else_branch, env)

        if isinstance(expression, CallExpr):
            callee = self.evaluate(expression.callee, env)
            args = [self.evaluate(arg, env) for arg in expression.args]
            return self._call_value(callee, args)

        if isinstance(expression, GetAttrExpr):
            obj = self.evaluate(expression.obj, env)
            return get_member(obj, expression.name)

        if isinstance(expression, IndexExpr):
            obj = self.evaluate(expression.obj, env)
            index = self.evaluate(expression.index, env)
            return get_index(obj, index)

        if isinstance(expression, NewExpr):
            callee = self.evaluate(expression.callee, env)
            args = [self.evaluate(arg, env) for arg in expression.args]
            if isinstance(callee, CallableValue):
                return callee.call(self, args)
            raise TurkCodeRuntimeError("'yeni' yalnizca siniflar icin kullanilabilir")

        raise TurkCodeRuntimeError(f"Bilinmeyen ifade dugumu: {type(expression).__name__}")

    def _assign(self, target: Expr, operator: str, value_expr: Expr, env: Environment) -> Any:
        value = self.evaluate(value_expr, env)
        current = None
        if operator != "EQUAL":
            current = self._read_target(target, env)
            if operator == "PLUS_EQUAL":
                value = stringify(current) + stringify(value) if isinstance(current, str) or isinstance(value, str) else current + value
            elif operator == "MINUS_EQUAL":
                value = current - value
            elif operator == "STAR_EQUAL":
                value = current * value
            elif operator == "SLASH_EQUAL":
                value = current / value
            elif operator == "PERCENT_EQUAL":
                value = current % value
            else:
                raise TurkCodeRuntimeError(f"Desteklenmeyen atama operatoru: {operator}")

        return self._write_target(target, value, env)

    def _read_target(self, target: Expr, env: Environment) -> Any:
        if isinstance(target, VariableExpr):
            return env.get(target.name)
        if isinstance(target, GetAttrExpr):
            obj = self.evaluate(target.obj, env)
            return get_member(obj, target.name)
        if isinstance(target, IndexExpr):
            obj = self.evaluate(target.obj, env)
            index = self.evaluate(target.index, env)
            return get_index(obj, index)
        raise TurkCodeRuntimeError("Bu hedefe atama yapilamaz")

    def _write_target(self, target: Expr, value: Any, env: Environment) -> Any:
        if isinstance(target, VariableExpr):
            try:
                env.assign(target.name, value)
            except TurkCodeRuntimeError:
                env.define(target.name, value)
            if env is self.globals or self.globals.contains_here(target.name):
                self.degiskenler[target.name] = value
            return value
        if isinstance(target, GetAttrExpr):
            obj = self.evaluate(target.obj, env)
            return set_member(obj, target.name, value)
        if isinstance(target, IndexExpr):
            obj = self.evaluate(target.obj, env)
            index = self.evaluate(target.index, env)
            return set_index(obj, index, value)
        raise TurkCodeRuntimeError("Bu hedefe atama yapilamaz")

    def _call_value(self, callee: Any, args: List[Any]) -> Any:
        if isinstance(callee, CallableValue):
            return callee.call(self, args)
        if callable(callee):
            try:
                return wrap_value(callee(*[unwrap_value(arg) for arg in args]))
            except TurkCodeError:
                raise
            except TypeError as exc:
                raise TurkCodeRuntimeError(f"Python cagrisi gecersiz: {exc}") from exc
            except Exception as exc:
                raise TurkCodeRuntimeError(f"Python cagrisi basarisiz: {exc}") from exc
        raise TurkCodeRuntimeError(f"Cagrilabilir olmayan deger: {stringify(callee)}")

    @staticmethod
    def _truthy(value: Any) -> bool:
        return bool(value)

    def _handle_catch(self, statement: TryCatchStmt, error_value: Any, env: Environment) -> Any:
        catch_env = Environment(env)
        if statement.error_name:
            catch_env.define(statement.error_name, stringify(error_value))
        return self.execute_block(statement.catch_block, catch_env)

    def _execute_import(self, statement: ImportStmt, env: Environment) -> Any:
        path_value = self.evaluate(statement.path, env)
        if not isinstance(path_value, str):
            raise TurkCodeRuntimeError("ithal yalnizca metin dosya yollari ile kullanilir")

        module = self._load_module(path_value)
        if statement.alias:
            env.define(statement.alias, module)
            if env is self.globals:
                self.degiskenler[statement.alias] = module
            return module

        for name, value in module.members.items():
            if env.contains_here(name):
                env.assign(name, value)
            else:
                env.define(name, value)
            if env is self.globals:
                self.degiskenler[name] = value
        return module

    def _load_module(self, raw_path: str) -> TurkModule:
        resolved = self._resolve_import_path(raw_path)
        cache_key = str(resolved)
        if cache_key in self.import_cache:
            return self.import_cache[cache_key]
        if cache_key in self._import_stack:
            raise TurkCodeRuntimeError(f"Dairesel ithal tespit edildi: {resolved}")
        if not resolved.exists():
            try:
                return self._load_python_module(raw_path)
            except TurkCodeRuntimeError as exc:
                raise TurkCodeRuntimeError(
                    f"Ithal edilecek dosya veya Python kutuphanesi bulunamadi: {raw_path}"
                ) from exc

        module_env = Environment(self.globals)
        module = TurkModule(resolved.stem)
        self.import_cache[cache_key] = module
        self._import_stack.append(cache_key)
        try:
            self.calistir_dosya(str(resolved), env=module_env)
            for name, value in module_env.values.items():
                if not name.startswith("_"):
                    module.set_member(name, value)
        except Exception:
            self.import_cache.pop(cache_key, None)
            raise
        finally:
            self._import_stack.pop()
        return module

    def _load_python_module(self, raw_name: str) -> PythonModule:
        module_name = _normalize_python_module_name(raw_name)
        cache_key = f"python:{module_name}"
        if cache_key in self.import_cache:
            return self.import_cache[cache_key]  # type: ignore[return-value]

        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            raise TurkCodeRuntimeError(f"Python kutuphanesi yuklenemedi: {module_name}") from exc

        wrapped_module = PythonModule(module, module_name)
        self.import_cache[cache_key] = wrapped_module
        return wrapped_module

    def _resolve_import_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path)
        if not candidate.suffix:
            candidate = candidate.with_suffix(".tc")

        bases: List[Path] = []
        if self._source_stack and self._source_stack[-1] is not None:
            bases.append(self._source_stack[-1].parent)
        if self.workspace_root is not None:
            bases.append(self.workspace_root)
        bases.append(Path.cwd())

        if candidate.is_absolute():
            return candidate.resolve()

        for base in bases:
            resolved = (base / candidate).resolve()
            if resolved.exists():
                return resolved
        return (bases[0] / candidate).resolve()

    def _map_values(self, func: Any, values: Any) -> List[Any]:
        return [self._call_value(func, [wrap_value(item)]) for item in list(unwrap_value(values))]

    def _filter_values(self, func: Any, values: Any) -> List[Any]:
        result = []
        for item in list(unwrap_value(values)):
            wrapped = wrap_value(item)
            if self._truthy(self._call_value(func, [wrapped])):
                result.append(wrapped)
        return result

    def _reduce_values(self, func: Any, values: Any, initial: Any = None) -> Any:
        items = [wrap_value(item) for item in list(unwrap_value(values))]
        if not items and initial is None:
            raise TurkCodeRuntimeError("azalt icin bos liste ve baslangic degeri verilemez")
        iterator = iter(items)
        accumulator = wrap_value(initial) if initial is not None else next(iterator)
        for item in iterator:
            accumulator = self._call_value(func, [accumulator, item])
        return accumulator

    @staticmethod
    def _range_values(start: Any, stop: Any = None, step: Any = 1) -> List[int]:
        if stop is None:
            return list(range(int(start)))
        return list(range(int(start), int(stop), int(step)))

    @staticmethod
    def _list_remove(values: Any, index: Any) -> List[Any]:
        data = list(values)
        del data[int(index)]
        return data

    @staticmethod
    def _slice(value: Any, start: Any, end: Any = None) -> Any:
        start_i = int(start)
        end_i = None if end is None else int(end)
        return value[start_i:end_i]

    @staticmethod
    def _join_or_concat(first: Any, second: Any) -> Any:
        if isinstance(first, list) and isinstance(second, list):
            return first + second
        if isinstance(first, list) and isinstance(second, str):
            return second.join(str(item) for item in first)
        return str(first) + str(second)

    @staticmethod
    def _substring(text: Any, start: Any, length: Any = None) -> str:
        source = str(text)
        start_i = int(start)
        if length is None:
            return source[start_i:]
        end_i = start_i + int(length)
        return source[start_i:end_i]

    def _type_name(self, value: Any) -> str:
        value = wrap_value(value)
        if value is None:
            return "bos"
        if isinstance(value, bool):
            return "mantiksal"
        if isinstance(value, int):
            return "tam"
        if isinstance(value, float):
            return "ondalik"
        if isinstance(value, str):
            return "metin"
        if isinstance(value, list):
            return "liste"
        if isinstance(value, TurkMap):
            return "nesne"
        if isinstance(value, PythonModule):
            return "kutuphane"
        if isinstance(value, TurkModule):
            return "modul"
        if isinstance(value, UserClass):
            return "sinif"
        if isinstance(value, TurkInstance):
            return value.klass.name
        if isinstance(value, CallableValue):
            return "fonksiyon"
        return type(value).__name__

    def _builtin_library(self, name: Any) -> PythonModule:
        if not isinstance(name, str):
            raise TurkCodeRuntimeError("kutuphane metin turunde bir Python kutuphanesi adi bekler")
        return self._load_python_module(name)

    @staticmethod
    def _builtin_print(*values: Any) -> None:
        print(" ".join(stringify(value) for value in values))

    @staticmethod
    def _builtin_input(prompt: Any = "") -> str:
        return input(stringify(prompt))


def repl() -> None:
    interpreter = TurkCodeInterpreter()
    print("TurkCode Etkilesimli Mod")
    print("Cikmak icin: cik")
    print("-" * 32)

    buffer: List[str] = []
    brace_balance = 0

    while True:
        prompt = "... " if buffer else ">>> "
        try:
            line = input(prompt)
        except EOFError:
            print()
            break

        if not buffer and line.strip() == "cik":
            break

        buffer.append(line)
        brace_balance += line.count("{") - line.count("}")

        if brace_balance > 0:
            continue

        source = "\n".join(buffer)
        buffer.clear()
        brace_balance = 0

        if not source.strip():
            continue

        try:
            result = interpreter.calistir(source)
            if result is not None:
                print(stringify(result))
        except TurkCodeError as exc:
            print(f"Hata: {exc}")
        except Exception as exc:
            print(f"Beklenmeyen hata: {exc}")


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv:
        print("TurkCode Interpreter")
        print("Kullanim:")
        print("  python interpreter.py <dosya.tc>")
        print("  python interpreter.py -i")
        return 0

    if argv[0] == "-i":
        repl()
        return 0

    path = Path(argv[0])
    if not path.exists():
        print(f"Hata: {path} bulunamadi")
        return 1

    interpreter = TurkCodeInterpreter()
    try:
        interpreter.calistir_dosya(str(path))
        return 0
    except TurkCodeError as exc:
        print(f"Hata: {exc}")
        return 1
    except Exception as exc:
        print(f"Beklenmeyen hata: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
