from __future__ import print_function
# -*- coding: windows-1252 -*-

from .antlr import EOF, CommonToken as Tok, TokenStream, TokenStreamException
from . import ExcelFormulaParser
from re import compile as recompile, IGNORECASE, VERBOSE


int_const_pattern = r"\d+\b"
flt_const_pattern = r"""
    (?:
        (?: \d* \. \d+ ) # .1 .12 .123 etc 9.1 etc 98.1 etc
        |
        (?: \d+ \. ) # 1. 12. 123. etc
    )
    # followed by optional exponent part
    (?: [Ee] [+-]? \d+ ) ?
    """
str_const_pattern = r'"(?:[^"]|"")*"'
#range2d_pattern   = recompile(r"\$?[A-I]?[A-Z]\$?\d+:\$?[A-I]?[A-Z]\$?\d+"
ref2d_r1c1_pattern = r"[Rr]0*[1-9][0-9]*[Cc]0*[1-9][0-9]*"
ref2d_pattern     = r"\$?[A-I]?[A-Z]\$?0*[1-9][0-9]*"
true_pattern      = r"TRUE\b"
false_pattern     = r"FALSE\b"
if_pattern        = r"IF\b"
choose_pattern    = r"CHOOSE\b"
name_pattern      = r"\w[\.\w]*"
quotename_pattern = r"'(?:[^']|'')*'" #### It's essential that this bracket be non-grouping.
ne_pattern        = r"<>"
ge_pattern        = r">="
le_pattern        = r"<="

pattern_type_tuples = (
    (flt_const_pattern, ExcelFormulaParser.NUM_CONST),
    (int_const_pattern, ExcelFormulaParser.INT_CONST),
    (str_const_pattern, ExcelFormulaParser.STR_CONST),
#    (range2d_pattern  , ExcelFormulaParser.RANGE2D),
    (ref2d_r1c1_pattern, ExcelFormulaParser.REF2D_R1C1),
    (ref2d_pattern    , ExcelFormulaParser.REF2D),
    (true_pattern     , ExcelFormulaParser.TRUE_CONST),
    (false_pattern    , ExcelFormulaParser.FALSE_CONST),
    (if_pattern       , ExcelFormulaParser.FUNC_IF),
    (choose_pattern   , ExcelFormulaParser.FUNC_CHOOSE),
    (name_pattern     , ExcelFormulaParser.NAME),
    (quotename_pattern, ExcelFormulaParser.QUOTENAME),
    (ne_pattern,        ExcelFormulaParser.NE),
    (ge_pattern,        ExcelFormulaParser.GE),
    (le_pattern,        ExcelFormulaParser.LE),
)

_re = recompile(
    '(' + ')|('.join(i[0] for i in pattern_type_tuples) + ')',
    VERBOSE+IGNORECASE)

_toktype = [None] + [i[1] for i in pattern_type_tuples]
# need dummy at start because re.MatchObject.lastindex counts from 1

single_char_lookup = {
    '=': ExcelFormulaParser.EQ,
    '<': ExcelFormulaParser.LT,
    '>': ExcelFormulaParser.GT,
    '+': ExcelFormulaParser.ADD,
    '-': ExcelFormulaParser.SUB,
    '*': ExcelFormulaParser.MUL,
    '/': ExcelFormulaParser.DIV,
    ':': ExcelFormulaParser.COLON,
    ';': ExcelFormulaParser.SEMICOLON,
    ',': ExcelFormulaParser.COMMA,
    '(': ExcelFormulaParser.LP,
    ')': ExcelFormulaParser.RP,
    '&': ExcelFormulaParser.CONCAT,
    '%': ExcelFormulaParser.PERCENT,
    '^': ExcelFormulaParser.POWER,
    '!': ExcelFormulaParser.BANG,
    }

class Lexer(TokenStream):
    def __init__(self, text):
        self._text = text[:]
        self._pos = 0
        self._line = 0

    def isEOF(self):
        return len(self._text) <= self._pos

    def curr_ch(self):
        return self._text[self._pos]

    def next_ch(self, n = 1):
        self._pos += n

    def is_whitespace(self):
        return self.curr_ch() in " \t\n\r\f\v"

    def match_pattern(self):
        m = _re.match(self._text, self._pos)
        if not m:
            return None
        self._pos = m.end(0)
        return Tok(type = _toktype[m.lastindex], text = m.group(0), col = m.start(0) + 1)

    def nextToken(self):
        # skip whitespace
        while not self.isEOF() and self.is_whitespace():
            self.next_ch()
        if self.isEOF():
            return Tok(type = EOF)
        # first, try to match token with 2 or more chars
        t = self.match_pattern()
        if t:
            return t
        # second, we want 1-char tokens
        te = self.curr_ch()
        try:
            ty = single_char_lookup[te]
        except KeyError:
            raise TokenStreamException(
                "Unexpected char %r in column %u." % (self.curr_ch(), self._pos))
        self.next_ch()
        return Tok(type=ty, text=te, col=self._pos)

if __name__ == '__main__':
    try:
        for t in Lexer(""" 1.23 456 "abcd" R2C2 a1 iv65536 true false if choose a_name 'qname' <> >= <= """):
            print(t)
    except TokenStreamException as e:
        print("error:", e)
