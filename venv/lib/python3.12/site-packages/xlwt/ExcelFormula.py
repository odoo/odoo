# -*- coding: windows-1252 -*-

from . import ExcelFormulaParser, ExcelFormulaLexer
import struct
from .antlr import ANTLRException


class Formula(object):
    __slots__ = ["__s", "__parser", "__sheet_refs", "__xcall_refs"]


    def __init__(self, s):
        try:
            self.__s = s
            lexer = ExcelFormulaLexer.Lexer(s)
            self.__parser = ExcelFormulaParser.Parser(lexer)
            self.__parser.formula()
            self.__sheet_refs = self.__parser.sheet_references
            self.__xcall_refs = self.__parser.xcall_references
        except ANTLRException as e:
            # print e
            raise ExcelFormulaParser.FormulaParseException("can't parse formula " + s)

    def get_references(self):
        return self.__sheet_refs, self.__xcall_refs

    def patch_references(self, patches):
        for offset, idx in patches:
            self.__parser.rpn = self.__parser.rpn[:offset] + struct.pack('<H', idx) + self.__parser.rpn[offset+2:]

    def text(self):
        return self.__s

    def rpn(self):
        '''
        Offset    Size    Contents
        0         2       Size of the following formula data (sz)
        2         sz      Formula data (RPN token array)
        [2+sz]    var.    (optional) Additional data for specific tokens

        '''
        return struct.pack("<H", len(self.__parser.rpn)) + self.__parser.rpn

