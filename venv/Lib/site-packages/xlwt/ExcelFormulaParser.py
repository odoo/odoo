### $ANTLR 2.7.7 (20060930): "xlwt/excel-formula.g" -> "ExcelFormulaParser.py"$
### import antlr and other modules ..
from . import antlr

### header action >>>
import struct
from . import Utils
from .UnicodeUtils import upack1
from .ExcelMagic import *

_RVAdelta =     {"R": 0, "V": 0x20, "A": 0x40}
_RVAdeltaRef =  {"R": 0, "V": 0x20, "A": 0x40, "D": 0x20}
_RVAdeltaArea = {"R": 0, "V": 0x20, "A": 0x40, "D": 0}


class FormulaParseException(Exception):
   """
   An exception indicating that a Formula could not be successfully parsed.
   """
### header action <<<
### preamble action>>>

### preamble action <<<

### >>>The Known Token Types <<<
SKIP                = antlr.SKIP
INVALID_TYPE        = antlr.INVALID_TYPE
EOF_TYPE            = antlr.EOF_TYPE
EOF                 = antlr.EOF
NULL_TREE_LOOKAHEAD = antlr.NULL_TREE_LOOKAHEAD
MIN_USER_TYPE       = antlr.MIN_USER_TYPE
TRUE_CONST = 4
FALSE_CONST = 5
STR_CONST = 6
NUM_CONST = 7
INT_CONST = 8
FUNC_IF = 9
FUNC_CHOOSE = 10
NAME = 11
QUOTENAME = 12
EQ = 13
NE = 14
GT = 15
LT = 16
GE = 17
LE = 18
ADD = 19
SUB = 20
MUL = 21
DIV = 22
POWER = 23
PERCENT = 24
LP = 25
RP = 26
LB = 27
RB = 28
COLON = 29
COMMA = 30
SEMICOLON = 31
REF2D = 32
REF2D_R1C1 = 33
BANG = 34
CONCAT = 35

class Parser(antlr.LLkParser):
    ### user action >>>
    ### user action <<<

    def __init__(self, *args, **kwargs):
        antlr.LLkParser.__init__(self, *args, **kwargs)
        self.tokenNames = _tokenNames
        ### __init__ header action >>>
        self.rpn = b""
        self.sheet_references = []
        self.xcall_references = []
        ### __init__ header action <<<

    def formula(self):

        pass
        self.expr("V")

    def expr(self,
        arg_type
    ):

        pass
        self.prec0_expr(arg_type)
        while True:
            if ((self.LA(1) >= EQ and self.LA(1) <= LE)):
                pass
                la1 = self.LA(1)
                if False:
                    pass
                elif la1 and la1 in [EQ]:
                    pass
                    self.match(EQ)
                    op = struct.pack('B', ptgEQ)
                elif la1 and la1 in [NE]:
                    pass
                    self.match(NE)
                    op = struct.pack('B', ptgNE)
                elif la1 and la1 in [GT]:
                    pass
                    self.match(GT)
                    op = struct.pack('B', ptgGT)
                elif la1 and la1 in [LT]:
                    pass
                    self.match(LT)
                    op = struct.pack('B', ptgLT)
                elif la1 and la1 in [GE]:
                    pass
                    self.match(GE)
                    op = struct.pack('B', ptgGE)
                elif la1 and la1 in [LE]:
                    pass
                    self.match(LE)
                    op = struct.pack('B', ptgLE)
                else:
                        raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                self.prec0_expr(arg_type)
                self.rpn += op
            else:
                break


    def prec0_expr(self,
        arg_type
    ):

        pass
        self.prec1_expr(arg_type)
        while True:
            if (self.LA(1)==CONCAT):
                pass
                pass
                self.match(CONCAT)
                op = struct.pack('B', ptgConcat)
                self.prec1_expr(arg_type)
                self.rpn += op
            else:
                break


    def prec1_expr(self,
        arg_type
    ):

        pass
        self.prec2_expr(arg_type)
        while True:
            if (self.LA(1)==ADD or self.LA(1)==SUB):
                pass
                la1 = self.LA(1)
                if False:
                    pass
                elif la1 and la1 in [ADD]:
                    pass
                    self.match(ADD)
                    op = struct.pack('B', ptgAdd)
                elif la1 and la1 in [SUB]:
                    pass
                    self.match(SUB)
                    op = struct.pack('B', ptgSub)
                else:
                        raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                self.prec2_expr(arg_type)
                self.rpn += op;
                          # print "**prec1_expr4 %s" % arg_type
            else:
                break


    def prec2_expr(self,
        arg_type
    ):

        pass
        self.prec3_expr(arg_type)
        while True:
            if (self.LA(1)==MUL or self.LA(1)==DIV):
                pass
                la1 = self.LA(1)
                if False:
                    pass
                elif la1 and la1 in [MUL]:
                    pass
                    self.match(MUL)
                    op = struct.pack('B', ptgMul)
                elif la1 and la1 in [DIV]:
                    pass
                    self.match(DIV)
                    op = struct.pack('B', ptgDiv)
                else:
                        raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                self.prec3_expr(arg_type)
                self.rpn += op
            else:
                break


    def prec3_expr(self,
        arg_type
    ):

        pass
        self.prec4_expr(arg_type)
        while True:
            if (self.LA(1)==POWER):
                pass
                pass
                self.match(POWER)
                op = struct.pack('B', ptgPower)
                self.prec4_expr(arg_type)
                self.rpn += op
            else:
                break


    def prec4_expr(self,
        arg_type
    ):

        pass
        self.prec5_expr(arg_type)
        la1 = self.LA(1)
        if False:
            pass
        elif la1 and la1 in [PERCENT]:
            pass
            self.match(PERCENT)
            self.rpn += struct.pack('B', ptgPercent)
        elif la1 and la1 in [EOF,EQ,NE,GT,LT,GE,LE,ADD,SUB,MUL,DIV,POWER,RP,COMMA,SEMICOLON,CONCAT]:
            pass
        else:
                raise antlr.NoViableAltException(self.LT(1), self.getFilename())


    def prec5_expr(self,
        arg_type
    ):

        la1 = self.LA(1)
        if False:
            pass
        elif la1 and la1 in [TRUE_CONST,FALSE_CONST,STR_CONST,NUM_CONST,INT_CONST,FUNC_IF,FUNC_CHOOSE,NAME,QUOTENAME,LP,REF2D]:
            pass
            self.primary(arg_type)
        elif la1 and la1 in [SUB]:
            pass
            self.match(SUB)
            self.primary(arg_type)
            self.rpn += struct.pack('B', ptgUminus)
        else:
                raise antlr.NoViableAltException(self.LT(1), self.getFilename())


    def primary(self,
        arg_type
    ):

        str_tok = None
        int_tok = None
        num_tok = None
        ref2d_tok = None
        ref2d1_tok = None
        ref2d2_tok = None
        ref3d_ref2d = None
        ref3d_ref2d2 = None
        name_tok = None
        func_tok = None
        la1 = self.LA(1)
        if False:
            pass
        elif la1 and la1 in [TRUE_CONST]:
            pass
            self.match(TRUE_CONST)
            self.rpn += struct.pack("2B", ptgBool, 1)
        elif la1 and la1 in [FALSE_CONST]:
            pass
            self.match(FALSE_CONST)
            self.rpn += struct.pack("2B", ptgBool, 0)
        elif la1 and la1 in [STR_CONST]:
            pass
            str_tok = self.LT(1)
            self.match(STR_CONST)
            self.rpn += struct.pack("B", ptgStr) + upack1(str_tok.text[1:-1].replace("\"\"", "\""))
        elif la1 and la1 in [NUM_CONST]:
            pass
            num_tok = self.LT(1)
            self.match(NUM_CONST)
            self.rpn += struct.pack("<Bd", ptgNum, float(num_tok.text))
        elif la1 and la1 in [FUNC_IF]:
            pass
            self.match(FUNC_IF)
            self.match(LP)
            self.expr("V")
            la1 = self.LA(1)
            if False:
                pass
            elif la1 and la1 in [SEMICOLON]:
                pass
                self.match(SEMICOLON)
            elif la1 and la1 in [COMMA]:
                pass
                self.match(COMMA)
            else:
                    raise antlr.NoViableAltException(self.LT(1), self.getFilename())

            self.rpn += struct.pack("<BBH", ptgAttr, 0x02, 0) # tAttrIf
            pos0 = len(self.rpn) - 2
            self.expr(arg_type)
            la1 = self.LA(1)
            if False:
                pass
            elif la1 and la1 in [SEMICOLON]:
                pass
                self.match(SEMICOLON)
            elif la1 and la1 in [COMMA]:
                pass
                self.match(COMMA)
            else:
                    raise antlr.NoViableAltException(self.LT(1), self.getFilename())

            self.rpn += struct.pack("<BBH", ptgAttr, 0x08, 0) # tAttrSkip
            pos1 = len(self.rpn) - 2
            self.rpn = self.rpn[:pos0] + struct.pack("<H", pos1-pos0) + self.rpn[pos0+2:]
            self.expr(arg_type)
            self.match(RP)
            self.rpn += struct.pack("<BBH", ptgAttr, 0x08, 3) # tAttrSkip
            self.rpn += struct.pack("<BBH", ptgFuncVarR, 3, 1) # 3 = nargs, 1 = IF func
            pos2 = len(self.rpn)
            self.rpn = self.rpn[:pos1] + struct.pack("<H", pos2-(pos1+2)-1) + self.rpn[pos1+2:]
        elif la1 and la1 in [FUNC_CHOOSE]:
            pass
            self.match(FUNC_CHOOSE)
            arg_type = "R"
            rpn_chunks = []
            self.match(LP)
            self.expr("V")
            rpn_start = len(self.rpn)
            ref_markers = [len(self.sheet_references)]
            while True:
                if (self.LA(1)==COMMA or self.LA(1)==SEMICOLON):
                    pass
                    la1 = self.LA(1)
                    if False:
                        pass
                    elif la1 and la1 in [SEMICOLON]:
                        pass
                        self.match(SEMICOLON)
                    elif la1 and la1 in [COMMA]:
                        pass
                        self.match(COMMA)
                    else:
                            raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                    mark = len(self.rpn)
                    la1 = self.LA(1)
                    if False:
                        pass
                    elif la1 and la1 in [TRUE_CONST,FALSE_CONST,STR_CONST,NUM_CONST,INT_CONST,FUNC_IF,FUNC_CHOOSE,NAME,QUOTENAME,SUB,LP,REF2D]:
                        pass
                        self.expr(arg_type)
                    elif la1 and la1 in [RP,COMMA,SEMICOLON]:
                        pass
                        self.rpn += struct.pack("B", ptgMissArg)
                    else:
                            raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                    rpn_chunks.append(self.rpn[mark:])
                    ref_markers.append(len(self.sheet_references))
                else:
                    break

            self.match(RP)
            self.rpn = self.rpn[:rpn_start]
            nc = len(rpn_chunks)
            chunklens = [len(chunk) for chunk in rpn_chunks]
            skiplens = [0] * nc
            skiplens[-1] = 3
            for ic in xrange(nc-1, 0, -1):
               skiplens[ic-1] = skiplens[ic] + chunklens[ic] + 4
            jump_pos = [2 * nc + 2]
            for ic in xrange(nc):
               jump_pos.append(jump_pos[-1] + chunklens[ic] + 4)
            chunk_shift = 2 * nc + 6 # size of tAttrChoose
            for ic in xrange(nc):
               for refx in xrange(ref_markers[ic], ref_markers[ic+1]):
                   ref = self.sheet_references[refx]
                   self.sheet_references[refx] = (ref[0], ref[1], ref[2] + chunk_shift)
               chunk_shift += 4 # size of tAttrSkip
            choose_rpn = []
            choose_rpn.append(struct.pack("<BBH", ptgAttr, 0x04, nc)) # 0x04 is tAttrChoose
            choose_rpn.append(struct.pack("<%dH" % (nc+1), *jump_pos))
            for ic in xrange(nc):
               choose_rpn.append(rpn_chunks[ic])
               choose_rpn.append(struct.pack("<BBH", ptgAttr, 0x08, skiplens[ic])) # 0x08 is tAttrSkip
            choose_rpn.append(struct.pack("<BBH", ptgFuncVarV, nc+1, 100)) # 100 is CHOOSE fn
            self.rpn += "".join(choose_rpn)
        elif la1 and la1 in [LP]:
            pass
            self.match(LP)
            self.expr(arg_type)
            self.match(RP)
            self.rpn += struct.pack("B", ptgParen)
        else:
            if (self.LA(1)==INT_CONST) and (_tokenSet_0.member(self.LA(2))):
                pass
                int_tok = self.LT(1)
                self.match(INT_CONST)
                # print "**int_const", int_tok.text
                int_value = int(int_tok.text)
                if int_value <= 65535:
                   self.rpn += struct.pack("<BH", ptgInt, int_value)
                else:
                   self.rpn += struct.pack("<Bd", ptgNum, float(int_value))
            elif (self.LA(1)==REF2D) and (_tokenSet_0.member(self.LA(2))):
                pass
                ref2d_tok = self.LT(1)
                self.match(REF2D)
                # print "**ref2d %s %s" % (ref2d_tok.text, arg_type)
                r, c = Utils.cell_to_packed_rowcol(ref2d_tok.text)
                ptg = ptgRefR + _RVAdeltaRef[arg_type]
                self.rpn += struct.pack("<B2H", ptg, r, c)
            elif (self.LA(1)==REF2D) and (self.LA(2)==COLON):
                pass
                ref2d1_tok = self.LT(1)
                self.match(REF2D)
                self.match(COLON)
                ref2d2_tok = self.LT(1)
                self.match(REF2D)
                r1, c1 = Utils.cell_to_packed_rowcol(ref2d1_tok.text)
                r2, c2 = Utils.cell_to_packed_rowcol(ref2d2_tok.text)
                ptg = ptgAreaR + _RVAdeltaArea[arg_type]
                self.rpn += struct.pack("<B4H", ptg, r1, r2, c1, c2)
            elif (self.LA(1)==INT_CONST or self.LA(1)==NAME or self.LA(1)==QUOTENAME) and (self.LA(2)==COLON or self.LA(2)==BANG):
                pass
                sheet1=self.sheet()
                sheet2 = sheet1
                la1 = self.LA(1)
                if False:
                    pass
                elif la1 and la1 in [COLON]:
                    pass
                    self.match(COLON)
                    sheet2=self.sheet()
                elif la1 and la1 in [BANG]:
                    pass
                else:
                        raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                self.match(BANG)
                ref3d_ref2d = self.LT(1)
                self.match(REF2D)
                ptg = ptgRef3dR + _RVAdeltaRef[arg_type]
                rpn_ref2d = ""
                r1, c1 = Utils.cell_to_packed_rowcol(ref3d_ref2d.text)
                rpn_ref2d = struct.pack("<3H", 0x0000, r1, c1)
                la1 = self.LA(1)
                if False:
                    pass
                elif la1 and la1 in [COLON]:
                    pass
                    self.match(COLON)
                    ref3d_ref2d2 = self.LT(1)
                    self.match(REF2D)
                    ptg = ptgArea3dR + _RVAdeltaArea[arg_type]
                    r2, c2 = Utils.cell_to_packed_rowcol(ref3d_ref2d2.text)
                    rpn_ref2d = struct.pack("<5H", 0x0000, r1, r2, c1, c2)
                elif la1 and la1 in [EOF,EQ,NE,GT,LT,GE,LE,ADD,SUB,MUL,DIV,POWER,PERCENT,RP,COMMA,SEMICOLON,CONCAT]:
                    pass
                else:
                        raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                self.rpn += struct.pack("<B", ptg)
                self.sheet_references.append((sheet1, sheet2, len(self.rpn)))
                self.rpn += rpn_ref2d
            elif (self.LA(1)==NAME) and (_tokenSet_0.member(self.LA(2))):
                pass
                name_tok = self.LT(1)
                self.match(NAME)
                raise Exception("[formula] found unexpected NAME token (%r)" % name_tok.txt)
                # #### TODO: handle references to defined names here
            elif (self.LA(1)==NAME) and (self.LA(2)==LP):
                pass
                func_tok = self.LT(1)
                self.match(NAME)
                func_toku = func_tok.text.upper()
                if func_toku in all_funcs_by_name:
                   (opcode,
                   min_argc,
                   max_argc,
                   func_type,
                   arg_type_str) = all_funcs_by_name[func_toku]
                   arg_type_list = list(arg_type_str)
                else:
                   raise Exception("[formula] unknown function (%s)" % func_tok.text)
                # print "**func_tok1 %s %s" % (func_toku, func_type)
                xcall = opcode < 0
                if xcall:
                   # The name of the add-in function is passed as the 1st arg
                   # of the hidden XCALL function
                   self.xcall_references.append((func_toku, len(self.rpn) + 1))
                   self.rpn += struct.pack("<BHHH",
                       ptgNameXR,
                       0xadde, # ##PATCHME## index to REF entry in EXTERNSHEET record
                       0xefbe, # ##PATCHME## one-based index to EXTERNNAME record
                       0x0000) # unused
                self.match(LP)
                arg_count=self.expr_list(arg_type_list, min_argc, max_argc)
                self.match(RP)
                if arg_count > max_argc or arg_count < min_argc:
                   raise Exception("%d parameters for function: %s" % (arg_count, func_tok.text))
                if xcall:
                   func_ptg = ptgFuncVarR + _RVAdelta[func_type]
                   self.rpn += struct.pack("<2BH", func_ptg, arg_count + 1, 255) # 255 is magic XCALL function
                elif min_argc == max_argc:
                   func_ptg = ptgFuncR + _RVAdelta[func_type]
                   self.rpn += struct.pack("<BH", func_ptg, opcode)
                elif arg_count == 1 and func_tok.text.upper() == "SUM":
                   self.rpn += struct.pack("<BBH", ptgAttr, 0x10, 0) # tAttrSum
                else:
                   func_ptg = ptgFuncVarR + _RVAdelta[func_type]
                   self.rpn += struct.pack("<2BH", func_ptg, arg_count, opcode)
            else:
                raise antlr.NoViableAltException(self.LT(1), self.getFilename())


    def sheet(self):
        ref = None

        sheet_ref_name = None
        sheet_ref_int = None
        sheet_ref_quote = None
        la1 = self.LA(1)
        if False:
            pass
        elif la1 and la1 in [NAME]:
            pass
            sheet_ref_name = self.LT(1)
            self.match(NAME)
            ref = sheet_ref_name.text
        elif la1 and la1 in [INT_CONST]:
            pass
            sheet_ref_int = self.LT(1)
            self.match(INT_CONST)
            ref = sheet_ref_int.text
        elif la1 and la1 in [QUOTENAME]:
            pass
            sheet_ref_quote = self.LT(1)
            self.match(QUOTENAME)
            ref = sheet_ref_quote.text[1:-1].replace("''", "'")
        else:
                raise antlr.NoViableAltException(self.LT(1), self.getFilename())

        return ref

    def expr_list(self,
        arg_type_list, min_argc, max_argc
    ):
        arg_cnt = None

        arg_cnt = 0
        arg_type = arg_type_list[arg_cnt]
        # print "**expr_list1[%d] req=%s" % (arg_cnt, arg_type)
        la1 = self.LA(1)
        if False:
            pass
        elif la1 and la1 in [TRUE_CONST,FALSE_CONST,STR_CONST,NUM_CONST,INT_CONST,FUNC_IF,FUNC_CHOOSE,NAME,QUOTENAME,SUB,LP,REF2D]:
            pass
            self.expr(arg_type)
            arg_cnt += 1
            while True:
                if (self.LA(1)==COMMA or self.LA(1)==SEMICOLON):
                    pass
                    if arg_cnt < len(arg_type_list):
                       arg_type = arg_type_list[arg_cnt]
                    else:
                       arg_type = arg_type_list[-1]
                    if arg_type == "+":
                       arg_type = arg_type_list[-2]
                    # print "**expr_list2[%d] req=%s" % (arg_cnt, arg_type)
                    la1 = self.LA(1)
                    if False:
                        pass
                    elif la1 and la1 in [SEMICOLON]:
                        pass
                        self.match(SEMICOLON)
                    elif la1 and la1 in [COMMA]:
                        pass
                        self.match(COMMA)
                    else:
                            raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                    la1 = self.LA(1)
                    if False:
                        pass
                    elif la1 and la1 in [TRUE_CONST,FALSE_CONST,STR_CONST,NUM_CONST,INT_CONST,FUNC_IF,FUNC_CHOOSE,NAME,QUOTENAME,SUB,LP,REF2D]:
                        pass
                        self.expr(arg_type)
                    elif la1 and la1 in [RP,COMMA,SEMICOLON]:
                        pass
                        self.rpn += struct.pack("B", ptgMissArg)
                    else:
                            raise antlr.NoViableAltException(self.LT(1), self.getFilename())

                    arg_cnt += 1
                else:
                    break

        elif la1 and la1 in [RP]:
            pass
        else:
                raise antlr.NoViableAltException(self.LT(1), self.getFilename())

        return arg_cnt


_tokenNames = [
    "<0>",
    "EOF",
    "<2>",
    "NULL_TREE_LOOKAHEAD",
    "TRUE_CONST",
    "FALSE_CONST",
    "STR_CONST",
    "NUM_CONST",
    "INT_CONST",
    "FUNC_IF",
    "FUNC_CHOOSE",
    "NAME",
    "QUOTENAME",
    "EQ",
    "NE",
    "GT",
    "LT",
    "GE",
    "LE",
    "ADD",
    "SUB",
    "MUL",
    "DIV",
    "POWER",
    "PERCENT",
    "LP",
    "RP",
    "LB",
    "RB",
    "COLON",
    "COMMA",
    "SEMICOLON",
    "REF2D",
    "REF2D_R1C1",
    "BANG",
    "CONCAT"
]


### generate bit set
def mk_tokenSet_0():
    ### var1
    data = [ 37681618946, 0]
    return data
_tokenSet_0 = antlr.BitSet(mk_tokenSet_0())

