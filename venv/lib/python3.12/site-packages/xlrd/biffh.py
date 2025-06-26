# -*- coding: utf-8 -*-
# Portions copyright © 2005-2010 Stephen John Machin, Lingfo Pty Ltd
# This module is part of the xlrd package, which is released under a
# BSD-style licence.
from __future__ import print_function

import sys
from struct import unpack

from .timemachine import *

DEBUG = 0



class XLRDError(Exception):
    """
    An exception indicating problems reading data from an Excel file.
    """


class BaseObject(object):
    """
    Parent of almost all other classes in the package. Defines a common
    :meth:`dump` method for debugging.
    """

    _repr_these = []


    def dump(self, f=None, header=None, footer=None, indent=0):
        """
        :param f: open file object, to which the dump is written
        :param header: text to write before the dump
        :param footer: text to write after the dump
        :param indent: number of leading spaces (for recursive calls)
        """
        if f is None:
            f = sys.stderr
        if hasattr(self, "__slots__"):
            alist = []
            for attr in self.__slots__:
                alist.append((attr, getattr(self, attr)))
        else:
            alist = self.__dict__.items()
        alist = sorted(alist)
        pad = " " * indent
        if header is not None: print(header, file=f)
        list_type = type([])
        dict_type = type({})
        for attr, value in alist:
            if getattr(value, 'dump', None) and attr != 'book':
                value.dump(f,
                    header="%s%s (%s object):" % (pad, attr, value.__class__.__name__),
                    indent=indent+4)
            elif (attr not in self._repr_these and
                  (isinstance(value, list_type) or isinstance(value, dict_type))):
                print("%s%s: %s, len = %d" % (pad, attr, type(value), len(value)), file=f)
            else:
                fprintf(f, "%s%s: %r\n", pad, attr, value)
        if footer is not None: print(footer, file=f)

FUN, FDT, FNU, FGE, FTX = range(5) # unknown, date, number, general, text
DATEFORMAT = FDT
NUMBERFORMAT = FNU

(
    XL_CELL_EMPTY,
    XL_CELL_TEXT,
    XL_CELL_NUMBER,
    XL_CELL_DATE,
    XL_CELL_BOOLEAN,
    XL_CELL_ERROR,
    XL_CELL_BLANK, # for use in debugging, gathering stats, etc
) = range(7)

biff_text_from_num = {
    0:  "(not BIFF)",
    20: "2.0",
    21: "2.1",
    30: "3",
    40: "4S",
    45: "4W",
    50: "5",
    70: "7",
    80: "8",
    85: "8X",
}

#: This dictionary can be used to produce a text version of the internal codes
#: that Excel uses for error cells.
error_text_from_code = {
    0x00: '#NULL!',  # Intersection of two cell ranges is empty
    0x07: '#DIV/0!', # Division by zero
    0x0F: '#VALUE!', # Wrong type of operand
    0x17: '#REF!',   # Illegal or deleted cell reference
    0x1D: '#NAME?',  # Wrong function or range name
    0x24: '#NUM!',   # Value range overflow
    0x2A: '#N/A',    # Argument or function not available
}

BIFF_FIRST_UNICODE = 80

XL_WORKBOOK_GLOBALS = WBKBLOBAL = 0x5
XL_WORKBOOK_GLOBALS_4W = 0x100
XL_WORKSHEET = WRKSHEET = 0x10

XL_BOUNDSHEET_WORKSHEET = 0x00
XL_BOUNDSHEET_CHART     = 0x02
XL_BOUNDSHEET_VB_MODULE = 0x06

# XL_RK2 = 0x7e
XL_ARRAY  = 0x0221
XL_ARRAY2 = 0x0021
XL_BLANK = 0x0201
XL_BLANK_B2 = 0x01
XL_BOF = 0x809
XL_BOOLERR = 0x205
XL_BOOLERR_B2 = 0x5
XL_BOUNDSHEET = 0x85
XL_BUILTINFMTCOUNT = 0x56
XL_CF = 0x01B1
XL_CODEPAGE = 0x42
XL_COLINFO = 0x7D
XL_COLUMNDEFAULT = 0x20 # BIFF2 only
XL_COLWIDTH = 0x24 # BIFF2 only
XL_CONDFMT = 0x01B0
XL_CONTINUE = 0x3c
XL_COUNTRY = 0x8C
XL_DATEMODE = 0x22
XL_DEFAULTROWHEIGHT = 0x0225
XL_DEFCOLWIDTH = 0x55
XL_DIMENSION = 0x200
XL_DIMENSION2 = 0x0
XL_EFONT = 0x45
XL_EOF = 0x0a
XL_EXTERNNAME = 0x23
XL_EXTERNSHEET = 0x17
XL_EXTSST = 0xff
XL_FEAT11 = 0x872
XL_FILEPASS = 0x2f
XL_FONT = 0x31
XL_FONT_B3B4 = 0x231
XL_FORMAT = 0x41e
XL_FORMAT2 = 0x1E # BIFF2, BIFF3
XL_FORMULA = 0x6
XL_FORMULA3 = 0x206
XL_FORMULA4 = 0x406
XL_GCW = 0xab
XL_HLINK = 0x01B8
XL_QUICKTIP = 0x0800
XL_HORIZONTALPAGEBREAKS = 0x1b
XL_INDEX = 0x20b
XL_INTEGER = 0x2 # BIFF2 only
XL_IXFE = 0x44 # BIFF2 only
XL_LABEL = 0x204
XL_LABEL_B2 = 0x04
XL_LABELRANGES = 0x15f
XL_LABELSST = 0xfd
XL_LEFTMARGIN = 0x26
XL_TOPMARGIN = 0x28
XL_RIGHTMARGIN = 0x27
XL_BOTTOMMARGIN = 0x29
XL_HEADER = 0x14
XL_FOOTER = 0x15
XL_HCENTER = 0x83
XL_VCENTER = 0x84
XL_MERGEDCELLS = 0xE5
XL_MSO_DRAWING = 0x00EC
XL_MSO_DRAWING_GROUP = 0x00EB
XL_MSO_DRAWING_SELECTION = 0x00ED
XL_MULRK = 0xbd
XL_MULBLANK = 0xbe
XL_NAME = 0x18
XL_NOTE = 0x1c
XL_NUMBER = 0x203
XL_NUMBER_B2 = 0x3
XL_OBJ = 0x5D
XL_PAGESETUP = 0xA1
XL_PALETTE = 0x92
XL_PANE = 0x41
XL_PRINTGRIDLINES = 0x2B
XL_PRINTHEADERS = 0x2A
XL_RK = 0x27e
XL_ROW = 0x208
XL_ROW_B2 = 0x08
XL_RSTRING = 0xd6
XL_SCL = 0x00A0
XL_SHEETHDR = 0x8F # BIFF4W only
XL_SHEETPR = 0x81
XL_SHEETSOFFSET = 0x8E # BIFF4W only
XL_SHRFMLA = 0x04bc
XL_SST = 0xfc
XL_STANDARDWIDTH = 0x99
XL_STRING = 0x207
XL_STRING_B2 = 0x7
XL_STYLE = 0x293
XL_SUPBOOK = 0x1AE # aka EXTERNALBOOK in OOo docs
XL_TABLEOP = 0x236
XL_TABLEOP2 = 0x37
XL_TABLEOP_B2 = 0x36
XL_TXO = 0x1b6
XL_UNCALCED = 0x5e
XL_UNKNOWN = 0xffff
XL_VERTICALPAGEBREAKS = 0x1a
XL_WINDOW2    = 0x023E
XL_WINDOW2_B2 = 0x003E
XL_WRITEACCESS = 0x5C
XL_WSBOOL = XL_SHEETPR
XL_XF = 0xe0
XL_XF2 = 0x0043 # BIFF2 version of XF record
XL_XF3 = 0x0243 # BIFF3 version of XF record
XL_XF4 = 0x0443 # BIFF4 version of XF record

boflen = {0x0809: 8, 0x0409: 6, 0x0209: 6, 0x0009: 4}
bofcodes = (0x0809, 0x0409, 0x0209, 0x0009)

XL_FORMULA_OPCODES = (0x0006, 0x0406, 0x0206)

_cell_opcode_list = [
    XL_BOOLERR,
    XL_FORMULA,
    XL_FORMULA3,
    XL_FORMULA4,
    XL_LABEL,
    XL_LABELSST,
    XL_MULRK,
    XL_NUMBER,
    XL_RK,
    XL_RSTRING,
]
_cell_opcode_dict = {}
for _cell_opcode in _cell_opcode_list:
    _cell_opcode_dict[_cell_opcode] = 1

def is_cell_opcode(c):
    return c in  _cell_opcode_dict

def upkbits(tgt_obj, src, manifest, local_setattr=setattr):
    for n, mask, attr in manifest:
        local_setattr(tgt_obj, attr, (src & mask) >> n)

def upkbitsL(tgt_obj, src, manifest, local_setattr=setattr, local_int=int):
    for n, mask, attr in manifest:
        local_setattr(tgt_obj, attr, local_int((src & mask) >> n))

def unpack_string(data, pos, encoding, lenlen=1):
    nchars = unpack('<' + 'BH'[lenlen-1], data[pos:pos+lenlen])[0]
    pos += lenlen
    return unicode(data[pos:pos+nchars], encoding)

def unpack_string_update_pos(data, pos, encoding, lenlen=1, known_len=None):
    if known_len is not None:
        # On a NAME record, the length byte is detached from the front of the string.
        nchars = known_len
    else:
        nchars = unpack('<' + 'BH'[lenlen-1], data[pos:pos+lenlen])[0]
        pos += lenlen
    newpos = pos + nchars
    return (unicode(data[pos:newpos], encoding), newpos)

def unpack_unicode(data, pos, lenlen=2):
    "Return unicode_strg"
    nchars = unpack('<' + 'BH'[lenlen-1], data[pos:pos+lenlen])[0]
    if not nchars:
        # Ambiguous whether 0-length string should have an "options" byte.
        # Avoid crash if missing.
        return UNICODE_LITERAL("")
    pos += lenlen
    options = BYTES_ORD(data[pos])
    pos += 1
    # phonetic = options & 0x04
    # richtext = options & 0x08
    if options & 0x08:
        # rt = unpack('<H', data[pos:pos+2])[0] # unused
        pos += 2
    if options & 0x04:
        # sz = unpack('<i', data[pos:pos+4])[0] # unused
        pos += 4
    if options & 0x01:
        # Uncompressed UTF-16-LE
        rawstrg = data[pos:pos+2*nchars]
        # if DEBUG: print "nchars=%d pos=%d rawstrg=%r" % (nchars, pos, rawstrg)
        strg = unicode(rawstrg, 'utf_16_le')
        # pos += 2*nchars
    else:
        # Note: this is COMPRESSED (not ASCII!) encoding!!!
        # Merely returning the raw bytes would work OK 99.99% of the time
        # if the local codepage was cp1252 -- however this would rapidly go pear-shaped
        # for other codepages so we grit our Anglocentric teeth and return Unicode :-)

        strg = unicode(data[pos:pos+nchars], "latin_1")
        # pos += nchars
    # if richtext:
    #     pos += 4 * rt
    # if phonetic:
    #     pos += sz
    # return (strg, pos)
    return strg

def unpack_unicode_update_pos(data, pos, lenlen=2, known_len=None):
    "Return (unicode_strg, updated value of pos)"
    if known_len is not None:
        # On a NAME record, the length byte is detached from the front of the string.
        nchars = known_len
    else:
        nchars = unpack('<' + 'BH'[lenlen-1], data[pos:pos+lenlen])[0]
        pos += lenlen
    if not nchars and not data[pos:]:
        # Zero-length string with no options byte
        return (UNICODE_LITERAL(""), pos)
    options = BYTES_ORD(data[pos])
    pos += 1
    phonetic = options & 0x04
    richtext = options & 0x08
    if richtext:
        rt = unpack('<H', data[pos:pos+2])[0]
        pos += 2
    if phonetic:
        sz = unpack('<i', data[pos:pos+4])[0]
        pos += 4
    if options & 0x01:
        # Uncompressed UTF-16-LE
        strg = unicode(data[pos:pos+2*nchars], 'utf_16_le')
        pos += 2*nchars
    else:
        # Note: this is COMPRESSED (not ASCII!) encoding!!!
        strg = unicode(data[pos:pos+nchars], "latin_1")
        pos += nchars
    if richtext:
        pos += 4 * rt
    if phonetic:
        pos += sz
    return (strg, pos)

def unpack_cell_range_address_list_update_pos(output_list, data, pos, biff_version, addr_size=6):
    # output_list is updated in situ
    assert addr_size in (6, 8)
    # Used to assert size == 6 if not BIFF8, but pyWLWriter writes
    # BIFF8-only MERGEDCELLS records in a BIFF5 file!
    n, = unpack("<H", data[pos:pos+2])
    pos += 2
    if n:
        if addr_size == 6:
            fmt = "<HHBB"
        else:
            fmt = "<HHHH"
        for _unused in xrange(n):
            ra, rb, ca, cb = unpack(fmt, data[pos:pos+addr_size])
            output_list.append((ra, rb+1, ca, cb+1))
            pos += addr_size
    return pos

_brecstrg = """\
0000 DIMENSIONS_B2
0001 BLANK_B2
0002 INTEGER_B2_ONLY
0003 NUMBER_B2
0004 LABEL_B2
0005 BOOLERR_B2
0006 FORMULA
0007 STRING_B2
0008 ROW_B2
0009 BOF_B2
000A EOF
000B INDEX_B2_ONLY
000C CALCCOUNT
000D CALCMODE
000E PRECISION
000F REFMODE
0010 DELTA
0011 ITERATION
0012 PROTECT
0013 PASSWORD
0014 HEADER
0015 FOOTER
0016 EXTERNCOUNT
0017 EXTERNSHEET
0018 NAME_B2,5+
0019 WINDOWPROTECT
001A VERTICALPAGEBREAKS
001B HORIZONTALPAGEBREAKS
001C NOTE
001D SELECTION
001E FORMAT_B2-3
001F BUILTINFMTCOUNT_B2
0020 COLUMNDEFAULT_B2_ONLY
0021 ARRAY_B2_ONLY
0022 DATEMODE
0023 EXTERNNAME
0024 COLWIDTH_B2_ONLY
0025 DEFAULTROWHEIGHT_B2_ONLY
0026 LEFTMARGIN
0027 RIGHTMARGIN
0028 TOPMARGIN
0029 BOTTOMMARGIN
002A PRINTHEADERS
002B PRINTGRIDLINES
002F FILEPASS
0031 FONT
0032 FONT2_B2_ONLY
0036 TABLEOP_B2
0037 TABLEOP2_B2
003C CONTINUE
003D WINDOW1
003E WINDOW2_B2
0040 BACKUP
0041 PANE
0042 CODEPAGE
0043 XF_B2
0044 IXFE_B2_ONLY
0045 EFONT_B2_ONLY
004D PLS
0051 DCONREF
0055 DEFCOLWIDTH
0056 BUILTINFMTCOUNT_B3-4
0059 XCT
005A CRN
005B FILESHARING
005C WRITEACCESS
005D OBJECT
005E UNCALCED
005F SAVERECALC
0063 OBJECTPROTECT
007D COLINFO
007E RK2_mythical_?
0080 GUTS
0081 WSBOOL
0082 GRIDSET
0083 HCENTER
0084 VCENTER
0085 BOUNDSHEET
0086 WRITEPROT
008C COUNTRY
008D HIDEOBJ
008E SHEETSOFFSET
008F SHEETHDR
0090 SORT
0092 PALETTE
0099 STANDARDWIDTH
009B FILTERMODE
009C FNGROUPCOUNT
009D AUTOFILTERINFO
009E AUTOFILTER
00A0 SCL
00A1 SETUP
00AB GCW
00BD MULRK
00BE MULBLANK
00C1 MMS
00D6 RSTRING
00D7 DBCELL
00DA BOOKBOOL
00DD SCENPROTECT
00E0 XF
00E1 INTERFACEHDR
00E2 INTERFACEEND
00E5 MERGEDCELLS
00E9 BITMAP
00EB MSO_DRAWING_GROUP
00EC MSO_DRAWING
00ED MSO_DRAWING_SELECTION
00EF PHONETIC
00FC SST
00FD LABELSST
00FF EXTSST
013D TABID
015F LABELRANGES
0160 USESELFS
0161 DSF
01AE SUPBOOK
01AF PROTECTIONREV4
01B0 CONDFMT
01B1 CF
01B2 DVAL
01B6 TXO
01B7 REFRESHALL
01B8 HLINK
01BC PASSWORDREV4
01BE DV
01C0 XL9FILE
01C1 RECALCID
0200 DIMENSIONS
0201 BLANK
0203 NUMBER
0204 LABEL
0205 BOOLERR
0206 FORMULA_B3
0207 STRING
0208 ROW
0209 BOF
020B INDEX_B3+
0218 NAME
0221 ARRAY
0223 EXTERNNAME_B3-4
0225 DEFAULTROWHEIGHT
0231 FONT_B3B4
0236 TABLEOP
023E WINDOW2
0243 XF_B3
027E RK
0293 STYLE
0406 FORMULA_B4
0409 BOF
041E FORMAT
0443 XF_B4
04BC SHRFMLA
0800 QUICKTIP
0809 BOF
0862 SHEETLAYOUT
0867 SHEETPROTECTION
0868 RANGEPROTECTION
"""

biff_rec_name_dict = {}
for _buff in _brecstrg.splitlines():
    _numh, _name = _buff.split()
    biff_rec_name_dict[int(_numh, 16)] = _name
del _buff, _name, _brecstrg

def hex_char_dump(strg, ofs, dlen, base=0, fout=sys.stdout, unnumbered=False):
    endpos = min(ofs + dlen, len(strg))
    pos = ofs
    numbered = not unnumbered
    num_prefix = ''
    while pos < endpos:
        endsub = min(pos + 16, endpos)
        substrg = strg[pos:endsub]
        lensub = endsub - pos
        if lensub <= 0 or lensub != len(substrg):
            fprintf(
                sys.stdout,
                '??? hex_char_dump: ofs=%d dlen=%d base=%d -> endpos=%d pos=%d endsub=%d substrg=%r\n',
                ofs, dlen, base, endpos, pos, endsub, substrg)
            break
        hexd = ''.join("%02x " % BYTES_ORD(c) for c in substrg)

        chard = ''
        for c in substrg:
            c = chr(BYTES_ORD(c))
            if c == '\0':
                c = '~'
            elif not (' ' <= c <= '~'):
                c = '?'
            chard += c
        if numbered:
            num_prefix = "%5d: " %  (base+pos-ofs)

        fprintf(fout, "%s     %-48s %s\n", num_prefix, hexd, chard)
        pos = endsub

def biff_dump(mem, stream_offset, stream_len, base=0, fout=sys.stdout, unnumbered=False):
    pos = stream_offset
    stream_end = stream_offset + stream_len
    adj = base - stream_offset
    dummies = 0
    numbered = not unnumbered
    num_prefix = ''
    while stream_end - pos >= 4:
        rc, length = unpack('<HH', mem[pos:pos+4])
        if rc == 0 and length == 0:
            if mem[pos:] == b'\0' * (stream_end - pos):
                dummies = stream_end - pos
                savpos = pos
                pos = stream_end
                break
            if dummies:
                dummies += 4
            else:
                savpos = pos
                dummies = 4
            pos += 4
        else:
            if dummies:
                if numbered:
                    num_prefix =  "%5d: " % (adj + savpos)
                fprintf(fout, "%s---- %d zero bytes skipped ----\n", num_prefix, dummies)
                dummies = 0
            recname = biff_rec_name_dict.get(rc, '<UNKNOWN>')
            if numbered:
                num_prefix = "%5d: " % (adj + pos)
            fprintf(fout, "%s%04x %s len = %04x (%d)\n", num_prefix, rc, recname, length, length)
            pos += 4
            hex_char_dump(mem, pos, length, adj+pos, fout, unnumbered)
            pos += length
    if dummies:
        if numbered:
            num_prefix =  "%5d: " % (adj + savpos)
        fprintf(fout, "%s---- %d zero bytes skipped ----\n", num_prefix, dummies)
    if pos < stream_end:
        if numbered:
            num_prefix = "%5d: " % (adj + pos)
        fprintf(fout, "%s---- Misc bytes at end ----\n", num_prefix)
        hex_char_dump(mem, pos, stream_end-pos, adj + pos, fout, unnumbered)
    elif pos > stream_end:
        fprintf(fout, "Last dumped record has length (%d) that is too large\n", length)

def biff_count_records(mem, stream_offset, stream_len, fout=sys.stdout):
    pos = stream_offset
    stream_end = stream_offset + stream_len
    tally = {}
    while stream_end - pos >= 4:
        rc, length = unpack('<HH', mem[pos:pos+4])
        if rc == 0 and length == 0:
            if mem[pos:] == b'\0' * (stream_end - pos):
                break
            recname = "<Dummy (zero)>"
        else:
            recname = biff_rec_name_dict.get(rc, None)
            if recname is None:
                recname = "Unknown_0x%04X" % rc
        if recname in tally:
            tally[recname] += 1
        else:
            tally[recname] = 1
        pos += length + 4
    slist = sorted(tally.items())
    for recname, count in slist:
        print("%8d %s" % (count, recname), file=fout)

encoding_from_codepage = {
    1200 : 'utf_16_le',
    10000: 'mac_roman',
    10006: 'mac_greek', # guess
    10007: 'mac_cyrillic', # guess
    10029: 'mac_latin2', # guess
    10079: 'mac_iceland', # guess
    10081: 'mac_turkish', # guess
    32768: 'mac_roman',
    32769: 'cp1252',
}
# some more guessing, for Indic scripts
# codepage 57000 range:
# 2 Devanagari [0]
# 3 Bengali [1]
# 4 Tamil [5]
# 5 Telegu [6]
# 6 Assamese [1] c.f. Bengali
# 7 Oriya [4]
# 8 Kannada [7]
# 9 Malayalam [8]
# 10 Gujarati [3]
# 11 Gurmukhi [2]
