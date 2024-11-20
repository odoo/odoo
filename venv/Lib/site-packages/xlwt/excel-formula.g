header {
    import struct
    import Utils
    from UnicodeUtils import upack1
    from ExcelMagic import *

    _RVAdelta =     {"R": 0, "V": 0x20, "A": 0x40}
    _RVAdeltaRef =  {"R": 0, "V": 0x20, "A": 0x40, "D": 0x20}
    _RVAdeltaArea = {"R": 0, "V": 0x20, "A": 0x40, "D": 0}

    
    class FormulaParseException(Exception):
        """
        An exception indicating that a Formula could not be successfully parsed.
        """
}

header "ExcelFormulaParser.__init__" {
    self.rpn = ""
    self.sheet_references = []
    self.xcall_references = []
}

options {
    language  = "Python";
}

class ExcelFormulaParser extends Parser;
options {
    k = 2;
    defaultErrorHandler = false;
    buildAST = false;
}


tokens {
    TRUE_CONST;
    FALSE_CONST;
    STR_CONST;
    NUM_CONST;
    INT_CONST;

    FUNC_IF;
    FUNC_CHOOSE;
    NAME;
    QUOTENAME;

    EQ;
    NE;
    GT;
    LT;
    GE;
    LE;

    ADD;
    SUB;
    MUL;
    DIV;

    POWER;
    PERCENT;

    LP;
    RP;

    LB;
    RB;

    COLON;
    COMMA;
    SEMICOLON;
    REF2D;
    REF2D_R1C1;
    BANG;
}

formula
    : expr["V"]
    ;

expr[arg_type]
    : // {print "\n**expr %s" % arg_type}
    prec0_expr[arg_type]
        (
            (
                  EQ { op = struct.pack('B', ptgEQ) }
                | NE { op = struct.pack('B', ptgNE) }
                | GT { op = struct.pack('B', ptgGT) }
                | LT { op = struct.pack('B', ptgLT) }
                | GE { op = struct.pack('B', ptgGE) }
                | LE { op = struct.pack('B', ptgLE) }
            )
            prec0_expr[arg_type] { self.rpn += op }
        )*
    ;

prec0_expr[arg_type]
    : prec1_expr[arg_type]
        (
            (
                CONCAT { op = struct.pack('B', ptgConcat) }
            )
            prec1_expr[arg_type] { self.rpn += op }
        )*
    ;

prec1_expr[arg_type]
    : // {print "**prec1_expr1 %s" % arg_type}
    prec2_expr[arg_type]
    // {print "**prec1_expr2 %s" % arg_type}
        (
            (
                  ADD { op = struct.pack('B', ptgAdd) }
                | SUB { op = struct.pack('B', ptgSub) }
            )
            // {print "**prec1_expr3 %s" % arg_type}
            prec2_expr[arg_type]
            { self.rpn += op;
            // print "**prec1_expr4 %s" % arg_type
            }
        )*
    ;


prec2_expr[arg_type]
    : prec3_expr[arg_type]
        (
            (
                  MUL { op = struct.pack('B', ptgMul) }
                | DIV { op = struct.pack('B', ptgDiv) }
            )
            prec3_expr[arg_type] { self.rpn += op }
        )*
    ;

prec3_expr[arg_type]
    : prec4_expr[arg_type]
        (
            (
                POWER { op = struct.pack('B', ptgPower) }
            )
            prec4_expr[arg_type] { self.rpn += op }
        )*
    ;

prec4_expr[arg_type]
    : prec5_expr[arg_type]
        (
            PERCENT { self.rpn += struct.pack('B', ptgPercent) }
        )?
    ;

prec5_expr[arg_type]
    : primary[arg_type]
    | SUB primary[arg_type] { self.rpn += struct.pack('B', ptgUminus) }
    ;

primary[arg_type]
    : TRUE_CONST
        {
            self.rpn += struct.pack("2B", ptgBool, 1)
        }
    | FALSE_CONST
        {
            self.rpn += struct.pack("2B", ptgBool, 0)
        }
    | str_tok:STR_CONST
        {
            self.rpn += struct.pack("B", ptgStr) + upack1(str_tok.text[1:-1].replace("\"\"", "\""))
        }
    | int_tok:INT_CONST
        {
            // print "**int_const", int_tok.text
            int_value = int(int_tok.text)
            if int_value <= 65535:
                self.rpn += struct.pack("<BH", ptgInt, int_value)
            else:
                self.rpn += struct.pack("<Bd", ptgNum, float(int_value))
        }
    | num_tok:NUM_CONST
        {
            self.rpn += struct.pack("<Bd", ptgNum, float(num_tok.text))
        }
    | ref2d_tok:REF2D
        {
            // print "**ref2d %s %s" % (ref2d_tok.text, arg_type)
            r, c = Utils.cell_to_packed_rowcol(ref2d_tok.text)
            ptg = ptgRefR + _RVAdeltaRef[arg_type]
            self.rpn += struct.pack("<B2H", ptg, r, c)
        }
    | ref2d1_tok:REF2D COLON ref2d2_tok:REF2D
        {
            r1, c1 = Utils.cell_to_packed_rowcol(ref2d1_tok.text)
            r2, c2 = Utils.cell_to_packed_rowcol(ref2d2_tok.text)
            ptg = ptgAreaR + _RVAdeltaArea[arg_type]
            self.rpn += struct.pack("<B4H", ptg, r1, r2, c1, c2)
        }
    | sheet1 = sheet
        { 
            sheet2 = sheet1
        }
        ( COLON sheet2 = sheet )? BANG ref3d_ref2d: REF2D
        {
            ptg = ptgRef3dR + _RVAdeltaRef[arg_type]
            rpn_ref2d = ""
            r1, c1 = Utils.cell_to_packed_rowcol(ref3d_ref2d.text)
            rpn_ref2d = struct.pack("<3H", 0x0000, r1, c1)
        }
        ( COLON ref3d_ref2d2: REF2D
            {
                ptg = ptgArea3dR + _RVAdeltaArea[arg_type]
                r2, c2 = Utils.cell_to_packed_rowcol(ref3d_ref2d2.text)
                rpn_ref2d = struct.pack("<5H", 0x0000, r1, r2, c1, c2)
            }
        )?
        {
            self.rpn += struct.pack("<B", ptg)
            self.sheet_references.append((sheet1, sheet2, len(self.rpn)))
            self.rpn += rpn_ref2d
        }
    | FUNC_IF
        LP expr["V"] (SEMICOLON | COMMA)
        {
            self.rpn += struct.pack("<BBH", ptgAttr, 0x02, 0) // tAttrIf
            pos0 = len(self.rpn) - 2
        }
        expr[arg_type] (SEMICOLON | COMMA)
        {
            self.rpn += struct.pack("<BBH", ptgAttr, 0x08, 0) // tAttrSkip
            pos1 = len(self.rpn) - 2
            self.rpn = self.rpn[:pos0] + struct.pack("<H", pos1-pos0) + self.rpn[pos0+2:]
        }
        expr[arg_type] RP
        {
            self.rpn += struct.pack("<BBH", ptgAttr, 0x08, 3) // tAttrSkip
            self.rpn += struct.pack("<BBH", ptgFuncVarR, 3, 1) // 3 = nargs, 1 = IF func
            pos2 = len(self.rpn)
            self.rpn = self.rpn[:pos1] + struct.pack("<H", pos2-(pos1+2)-1) + self.rpn[pos1+2:]
        }
    | FUNC_CHOOSE
        {
            arg_type = "R"
            rpn_chunks = []
        }
        LP expr["V"] // first argument (the selector)
        {
            rpn_start = len(self.rpn)
            ref_markers = [len(self.sheet_references)]
        }
        (
            (SEMICOLON | COMMA)
                { mark = len(self.rpn) }
                (
                  expr[arg_type]
                | { self.rpn += struct.pack("B", ptgMissArg) }
                )
                {
                    rpn_chunks.append(self.rpn[mark:])
                    ref_markers.append(len(self.sheet_references))
                }
        )*
        RP
        {
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
            chunk_shift = 2 * nc + 6 // size of tAttrChoose
            for ic in xrange(nc):
                for refx in xrange(ref_markers[ic], ref_markers[ic+1]):
                    ref = self.sheet_references[refx]
                    self.sheet_references[refx] = (ref[0], ref[1], ref[2] + chunk_shift)
                chunk_shift += 4 // size of tAttrSkip
            choose_rpn = []
            choose_rpn.append(struct.pack("<BBH", ptgAttr, 0x04, nc)) // 0x04 is tAttrChoose
            choose_rpn.append(struct.pack("<%dH" % (nc+1), *jump_pos))
            for ic in xrange(nc):
                choose_rpn.append(rpn_chunks[ic])
                choose_rpn.append(struct.pack("<BBH", ptgAttr, 0x08, skiplens[ic])) // 0x08 is tAttrSkip
            choose_rpn.append(struct.pack("<BBH", ptgFuncVarV, nc+1, 100)) // 100 is CHOOSE fn
            self.rpn += "".join(choose_rpn)
        }
    | name_tok:NAME
        {
            raise Exception("[formula] found unexpected NAME token (%r)" % name_tok.txt)
            // #### TODO: handle references to defined names here
        }
    | func_tok:NAME
        {
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
            // print "**func_tok1 %s %s" % (func_toku, func_type)
            xcall = opcode < 0
            if xcall:
                // The name of the add-in function is passed as the 1st arg
                // of the hidden XCALL function
                self.xcall_references.append((func_toku, len(self.rpn) + 1))
                self.rpn += struct.pack("<BHHH",
                    ptgNameXR,
                    0xadde, // ##PATCHME## index to REF entry in EXTERNSHEET record
                    0xefbe, // ##PATCHME## one-based index to EXTERNNAME record
                    0x0000) // unused
        }
        LP arg_count = expr_list[arg_type_list, min_argc, max_argc] RP
        {
            if arg_count > max_argc or arg_count < min_argc:
                raise Exception, "%d parameters for function: %s" % (arg_count, func_tok.text)
            if xcall:
                func_ptg = ptgFuncVarR + _RVAdelta[func_type]
                self.rpn += struct.pack("<2BH", func_ptg, arg_count + 1, 255) // 255 is magic XCALL function
            elif min_argc == max_argc:
                func_ptg = ptgFuncR + _RVAdelta[func_type]
                self.rpn += struct.pack("<BH", func_ptg, opcode)
            elif arg_count == 1 and func_tok.text.upper() == "SUM":
                self.rpn += struct.pack("<BBH", ptgAttr, 0x10, 0) // tAttrSum
            else:
                func_ptg = ptgFuncVarR + _RVAdelta[func_type]
                self.rpn += struct.pack("<2BH", func_ptg, arg_count, opcode)
        }
    | LP expr[arg_type] RP
        {
            self.rpn += struct.pack("B", ptgParen)
        }
    ;

expr_list[arg_type_list, min_argc, max_argc] returns [arg_cnt]
    {
        arg_cnt = 0
        arg_type = arg_type_list[arg_cnt]
        // print "**expr_list1[%d] req=%s" % (arg_cnt, arg_type)
    }
    : expr[arg_type] { arg_cnt += 1 }
    (
        {
            if arg_cnt < len(arg_type_list):
                arg_type = arg_type_list[arg_cnt]
            else:
                arg_type = arg_type_list[-1]
            if arg_type == "+":
                arg_type = arg_type_list[-2]
            // print "**expr_list2[%d] req=%s" % (arg_cnt, arg_type)
        }
        (SEMICOLON | COMMA)
            (
                  expr[arg_type]
                | { self.rpn += struct.pack("B", ptgMissArg) }
            )
            { arg_cnt += 1 }
    )*
    |
    ;

sheet returns[ref]
    : sheet_ref_name: NAME
    	{ ref = sheet_ref_name.text }
    | sheet_ref_int: INT_CONST
    	{ ref = sheet_ref_int.text }
    | sheet_ref_quote: QUOTENAME
    	{ ref = sheet_ref_quote.text[1:-1].replace("''", "'") }
    ;
