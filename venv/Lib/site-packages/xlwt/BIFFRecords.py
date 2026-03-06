# -*- coding: cp1252 -*-
from struct import pack
from .UnicodeUtils import upack1, upack2, upack2rt
from .compat import basestring, unicode, unicode_type, xrange, iteritems

class SharedStringTable(object):
    _SST_ID = 0x00FC
    _CONTINUE_ID = 0x003C

    def __init__(self, encoding):
        self.encoding = encoding
        self._str_indexes = {}
        self._rt_indexes = {}
        self._tally = []
        self._add_calls = 0
        # Following 3 attrs are used for temporary storage in the
        # get_biff_record() method and methods called by it. The pseudo-
        # initialisation here is for documentation purposes only.
        self._sst_record = None
        self._continues = None
        self._current_piece = None

    def add_str(self, s):
        if self.encoding != 'ascii' and not isinstance(s, unicode_type):
            s = unicode(s, self.encoding)
        self._add_calls += 1
        if s not in self._str_indexes:
            idx = len(self._str_indexes) + len(self._rt_indexes)
            self._str_indexes[s] = idx
            self._tally.append(1)
        else:
            idx = self._str_indexes[s]
            self._tally[idx] += 1
        return idx
	
    def add_rt(self, rt):
        rtList = []
        for s, xf in rt:
            if self.encoding != 'ascii' and not isinstance(s, unicode_type):
                s = unicode(s, self.encoding)
            rtList.append((s, xf))
        rt = tuple(rtList)
        self._add_calls += 1
        if rt not in self._rt_indexes:
            idx = len(self._str_indexes) + len(self._rt_indexes)
            self._rt_indexes[rt] = idx
            self._tally.append(1)
        else:
            idx = self._rt_indexes[rt]
            self._tally[idx] += 1
        return idx

    def del_str(self, idx):
        # This is called when we are replacing the contents of a string cell.
        # handles both regular and rt strings
        assert self._tally[idx] > 0
        self._tally[idx] -= 1
        self._add_calls -= 1

    def str_index(self, s):
        return self._str_indexes[s]

    def rt_index(self, rt):
        return self._rt_indexes[rt]

    def get_biff_record(self):
        self._sst_record = b''
        self._continues = [None, None]
        self._current_piece = pack('<II', 0, 0)
        data = [(idx, s) for s, idx in iteritems(self._str_indexes)]
        data.extend((idx, s) for s, idx in iteritems(self._rt_indexes))
        data.sort() # in index order
        for idx, s in data:
            if self._tally[idx] == 0:
                s = u''
            if isinstance(s, basestring):
                self._add_to_sst(s)
            else:
                self._add_rt_to_sst(s)
        del data
        self._new_piece()
        self._continues[0] = pack('<2HII', self._SST_ID, len(self._sst_record), self._add_calls, len(self._str_indexes) + len(self._rt_indexes))
        self._continues[1] = self._sst_record[8:]
        self._sst_record = None
        self._current_piece = None
        result = b''.join(self._continues)
        self._continues = None
        return result


    def _add_to_sst(self, s):
        u_str = upack2(s, self.encoding)

        is_unicode_str = u_str[2] == b'\x01'[0]
        if is_unicode_str:
            atom_len = 5 # 2 byte -- len,
                         # 1 byte -- options,
                         # 2 byte -- 1st sym
        else:
            atom_len = 4 # 2 byte -- len,
                         # 1 byte -- options,
                         # 1 byte -- 1st sym

        self._save_atom(u_str[0:atom_len])
        self._save_splitted(u_str[atom_len:], is_unicode_str)
	
    def _add_rt_to_sst(self, rt):
        rt_str, rt_fr = upack2rt(rt, self.encoding)
        is_unicode_str = rt_str[2] == b'\x09'[0]
        if is_unicode_str:
            atom_len = 7 # 2 byte -- len,
                         # 1 byte -- options,
                         # 2 byte -- number of rt runs
                         # 2 byte -- 1st sym
        else:
            atom_len = 6 # 2 byte -- len,
                         # 1 byte -- options,
                         # 2 byte -- number of rt runs
                         # 1 byte -- 1st sym
        self._save_atom(rt_str[0:atom_len])
        self._save_splitted(rt_str[atom_len:], is_unicode_str)
        for i in range(0, len(rt_fr), 4):
            self._save_atom(rt_fr[i:i+4])

    def _new_piece(self):
        if self._sst_record == b'':
            self._sst_record = self._current_piece
        else:
            curr_piece_len = len(self._current_piece)
            self._continues.append(pack('<2H%ds'%curr_piece_len, self._CONTINUE_ID, curr_piece_len, self._current_piece))
        self._current_piece = b''

    def _save_atom(self, s):
        atom_len = len(s)
        free_space = 0x2020 - len(self._current_piece)
        if free_space < atom_len:
            self._new_piece()
        self._current_piece += s

    def _save_splitted(self, s, is_unicode_str):
        i = 0
        str_len = len(s)
        while i < str_len:
            piece_len = len(self._current_piece)
            free_space = 0x2020 - piece_len
            tail_len = str_len - i
            need_more_space = free_space < tail_len

            if not need_more_space:
                atom_len = tail_len
            else:
                if is_unicode_str:
                    atom_len = free_space & 0xFFFE
                else:
                    atom_len = free_space

            self._current_piece += s[i:i+atom_len]

            if need_more_space:
                self._new_piece()
                if is_unicode_str:
                    self._current_piece += b'\x01'
                else:
                    self._current_piece += b'\x00'

            i += atom_len


class BiffRecord(object):

    _rec_data = b'' # class attribute; child classes need to set this.

    def get_rec_header(self):
        return pack('<2H', self._REC_ID, len(self._rec_data))

    # Not over-ridden by any child classes, never called (except by "get"; see below).
    # def get_rec_data(self):
    #     return self._rec_data

    def get(self):
        # data = self.get_rec_data()
        data = self._rec_data
        if len(data) > 0x2020: # limit for BIFF7/8
            chunks = []
            pos = 0
            while pos < len(data):
                chunk_pos = pos + 0x2020
                chunk = data[pos:chunk_pos]
                chunks.append(chunk)
                pos = chunk_pos
            continues = pack('<2H', self._REC_ID, len(chunks[0])) + chunks[0]
            for chunk in chunks[1:]:
                continues += pack('<2H%ds'%len(chunk), 0x003C, len(chunk), chunk)
                # 0x003C -- CONTINUE record id
            return continues
        else:
            return self.get_rec_header() + data


class Biff8BOFRecord(BiffRecord):
    """
    Offset Size Contents
    0      2    Version, contains 0600H for BIFF8 and BIFF8X
    2      2    Type of the following data:
                  0005H = Workbook globals
                  0006H = Visual Basic module
                  0010H = Worksheet
                  0020H = Chart
                  0040H = Macro sheet
                  0100H = Workspace file
    4      2    Build identifier
    6      2    Build year
    8      4    File history flags
    12     4    Lowest Excel version that can read all records in this file
    """
    _REC_ID      = 0x0809
    # stream types
    BOOK_GLOBAL = 0x0005
    VB_MODULE   = 0x0006
    WORKSHEET   = 0x0010
    CHART       = 0x0020
    MACROSHEET  = 0x0040
    WORKSPACE   = 0x0100

    def __init__(self, rec_type):
        version  = 0x0600
        build    = 0x0DBB
        year     = 0x07CC
        file_hist_flags = 0x00
        ver_can_read    = 0x06

        self._rec_data = pack('<4H2I', version, rec_type, build, year, file_hist_flags, ver_can_read)


class InteraceHdrRecord(BiffRecord):
    _REC_ID = 0x00E1

    def __init__(self):
        self._rec_data = pack('BB', 0xB0, 0x04)


class InteraceEndRecord(BiffRecord):
    _REC_ID = 0x00E2

    def __init__(self):
        self._rec_data = b''


class MMSRecord(BiffRecord):
    _REC_ID = 0x00C1

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class WriteAccessRecord(BiffRecord):
    """
    This record is part of the file protection. It contains the name of the
    user  that  has  saved  the  file. The user name is always stored as an
    equal-sized  string.  All  unused  characters after the name are filled
    with space characters. It is not required to write the mentioned string
    length. Every other length will be accepted too.
    """
    _REC_ID = 0x005C

    def __init__(self, owner):
        uowner = owner[0:0x30]
        uowner_len = len(uowner)
        if isinstance(uowner, unicode_type):
            uowner = uowner.encode('ascii')  # probably not ascii, but play it safe until we know more
        self._rec_data = pack('%ds%ds' % (uowner_len, 0x70 - uowner_len), uowner, b' '*(0x70 - uowner_len))


class DSFRecord(BiffRecord):
    """
    This  record  specifies  if the file contains an additional BIFF5/BIFF7
    workbook stream.
    Record DSF, BIFF8:
    Offset Size Contents
    0        2     0 = Only the BIFF8 Workbook stream is present
                   1 = Additional BIFF5/BIFF7 Book stream is in the file
    A  double  stream file can be read by Excel 5.0 and Excel 95, and still
    contains  all  new  features  added to BIFF8 (which are left out in the
    BIFF5/BIFF7 Book stream).
    """
    _REC_ID = 0x0161

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class TabIDRecord(BiffRecord):
    _REC_ID = 0x013D

    def __init__(self, sheetcount):
        for i in range(sheetcount):
            self._rec_data += pack('<H', i+1)


class FnGroupCountRecord(BiffRecord):
    _REC_ID = 0x009C

    def __init__(self):
        self._rec_data = pack('BB', 0x0E, 0x00)


class WindowProtectRecord(BiffRecord):
    """
    This record is part of the worksheet/workbook protection. It determines
    whether  the window configuration of this document is protected. Window
    protection is not active, if this record is omitted.
    """
    _REC_ID = 0x0019

    def __init__(self, wndprotect):
        self._rec_data = pack('<H', wndprotect)


class ObjectProtectRecord(BiffRecord):
    """
    This record is part of the worksheet/workbook protection.
    It determines whether the objects of the current sheet are protected.
    Object protection is not active, if this record is omitted.
    """
    _REC_ID = 0x0063


    def __init__(self, objprotect):
        self._rec_data = pack('<H', objprotect)


class ScenProtectRecord(BiffRecord):
    """
    This record is part of the worksheet/workbook protection. It
    determines whether the scenarios of the current sheet are protected.
    Scenario protection is not active, if this record is omitted.
    """
    _REC_ID = 0x00DD


    def __init__(self, scenprotect):
        self._rec_data = pack('<H', scenprotect)


class ProtectRecord(BiffRecord):
    """
    This  record is part of the worksheet/workbook protection. It specifies
    whether  a  worksheet  or a workbook is protected against modification.
    Protection is not active, if this record is omitted.
    """

    _REC_ID = 0x0012

    def __init__(self, protect):
        self._rec_data = pack('<H', protect)


class PasswordRecord(BiffRecord):
    """
    This record is part of the worksheet/workbook protection. It
    stores a 16-bit hash value, calculated from the worksheet or workbook
    protection password.
    """
    _REC_ID = 0x0013
    def passwd_hash(self, plaintext):
        """
        Based on the algorithm provided by Daniel Rentz of OpenOffice.
        """
        if plaintext == "":
            return 0

        passwd_hash = 0x0000
        for i, char in enumerate(plaintext):
            c = ord(char) << (i + 1)
            low_15 = c & 0x7fff
            high_15 = c & 0x7fff << 15
            high_15 = high_15 >> 15
            c = low_15 | high_15
            passwd_hash ^= c
        passwd_hash ^= len(plaintext)
        passwd_hash ^= 0xCE4B
        return passwd_hash

    def __init__(self, passwd = ""):
        self._rec_data = pack('<H', self.passwd_hash(passwd))


class Prot4RevRecord(BiffRecord):
    _REC_ID = 0x01AF

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class Prot4RevPassRecord(BiffRecord):
    _REC_ID = 0x01BC

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class BackupRecord(BiffRecord):
    """
    This  record  contains  a Boolean value determining whether Excel makes
    a backup of the file while saving.
    """
    _REC_ID = 0x0040

    def __init__(self, backup):
        self._rec_data = pack('<H', backup)

class HideObjRecord(BiffRecord):
    """
    This record specifies whether and how to show objects in the workbook.

    Record HIDEOBJ, BIFF3-BIFF8:
    Offset  Size    Contents
    0       2       Viewing mode for objects:
                        0 = Show all objects
                        1 = Show placeholders
                        2 = Do not show objects
    """
    _REC_ID = 0x008D

    def __init__(self):
        self._rec_data = pack('<H', 0x00)



class RefreshAllRecord(BiffRecord):
    """
    """

    _REC_ID = 0x01B7

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class BookBoolRecord(BiffRecord):
    """
    This record contains a Boolean value determining whether to save values
    linked  from external workbooks (CRN records and XCT records). In BIFF3
    and BIFF4 this option is stored in the WSBOOL record.

    Record BOOKBOOL, BIFF5-BIFF8:

    Offset  Size    Contents
    0       2       0 = Save external linked values;
                    1 = Do not save external linked values
    """

    _REC_ID = 0x00DA

    def __init__(self):
        self._rec_data = pack('<H', 0x00)


class CountryRecord(BiffRecord):
    """
    This   record   stores  two  Windows  country  identifiers.  The  first
    represents  the  user  interface language of the Excel version that has
    saved  the file, and the second represents the system regional settings
    at the time the file was saved.

    Record COUNTRY, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Windows country identifier of the user interface language of Excel
    2       2       Windows country identifier of the system regional settings

    The  following  table  shows most of the used country identifiers. Most
    of  these  identifiers  are  equal to the international country calling
    codes.

    1   USA
    2   Canada
    7   Russia
    """

    _REC_ID = 0x008C

    def __init__(self, ui_id, sys_settings_id):
        self._rec_data = pack('<2H', ui_id, sys_settings_id)


class UseSelfsRecord(BiffRecord):
    """
    This  record  specifies if the formulas in the workbook can use natural
    language  formulas.  This  type  of  formula can refer to cells by its
    content or the content of the column or row header cell.

    Record USESELFS, BIFF8:

    Offset  Size    Contents
    0       2       0 = Do not use natural language formulas
                    1 = Use natural language formulas

    """

    _REC_ID = 0x0160

    def __init__(self):
        self._rec_data = pack('<H', 0x01)


class EOFRecord(BiffRecord):
    _REC_ID = 0x000A

    def __init__(self):
        self._rec_data = b''


class DateModeRecord(BiffRecord):
    """
    This  record  specifies  the  base date for displaying date values. All
    dates  are  stored as count of days past this base date. In BIFF2-BIFF4
    this   record  is  part  of  the  Calculation  Settings  Block.
    In BIFF5-BIFF8 it is stored in the Workbook Globals Substream.

    Record DATEMODE, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = Base is 1899-Dec-31 (the cell = 1 represents 1900-Jan-01)
                    1 = Base is 1904-Jan-01 (the cell = 1 represents 1904-Jan-02)
    """
    _REC_ID = 0x0022

    def __init__(self, from1904):
        if from1904:
            self._rec_data = pack('<H', 1)
        else:
            self._rec_data = pack('<H', 0)


class PrecisionRecord(BiffRecord):
    """
    This record stores if formulas use the real cell values for calculation
    or  the  values  displayed  on  the screen. In BIFF2- BIFF4 this record
    is  part of the Calculation Settings Block. In BIFF5-BIFF8 it is stored
    in the Workbook Globals Substream.

    Record PRECISION, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = Use displayed values;
                    1 = Use real cell values
    """
    _REC_ID = 0x000E

    def __init__(self, use_real_values):
        if use_real_values:
            self._rec_data = pack('<H', 1)
        else:
            self._rec_data = pack('<H', 0)


class CodepageBiff8Record(BiffRecord):
    """
    This record stores the text encoding used to write byte strings, stored
    as MS Windows code page identifier. The CODEPAGE record in BIFF8 always
    contains  the  code  page  1200  (UTF-16).  Therefore  it is not
    possible  to  obtain the encoding used for a protection password (it is
    not UTF-16).

    Record CODEPAGE, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       Code page identifier used for byte string text encoding:
                      016FH = 367 = ASCII
                      01B5H = 437 = IBM PC CP-437 (US)
                      02D0H = 720 = IBM PC CP-720 (OEM Arabic)
                      02E1H = 737 = IBM PC CP-737 (Greek)
                      0307H = 775 = IBM PC CP-775 (Baltic)
                      0352H = 850 = IBM PC CP-850 (Latin I)
                      0354H = 852 = IBM PC CP-852 (Latin II (Central European))
                      0357H = 855 = IBM PC CP-855 (Cyrillic)
                      0359H = 857 = IBM PC CP-857 (Turkish)
                      035AH = 858 = IBM PC CP-858 (Multilingual Latin I with Euro)
                      035CH = 860 = IBM PC CP-860 (Portuguese)
                      035DH = 861 = IBM PC CP-861 (Icelandic)
                      035EH = 862 = IBM PC CP-862 (Hebrew)
                      035FH = 863 = IBM PC CP-863 (Canadian (French))
                      0360H = 864 = IBM PC CP-864 (Arabic)
                      0361H = 865 = IBM PC CP-865 (Nordic)
                      0362H = 866 = IBM PC CP-866 (Cyrillic (Russian))
                      0365H = 869 = IBM PC CP-869 (Greek (Modern))
                      036AH = 874 = Windows CP-874 (Thai)
                      03A4H = 932 = Windows CP-932 (Japanese Shift-JIS)
                      03A8H = 936 = Windows CP-936 (Chinese Simplified GBK)
                      03B5H = 949 = Windows CP-949 (Korean (Wansung))
                      03B6H = 950 = Windows CP-950 (Chinese Traditional BIG5)
                      04B0H = 1200 = UTF-16 (BIFF8)
                      04E2H = 1250 = Windows CP-1250 (Latin II) (Central European)
                      04E3H = 1251 = Windows CP-1251 (Cyrillic)
                      04E4H = 1252 = Windows CP-1252 (Latin I) (BIFF4-BIFF7)
                      04E5H = 1253 = Windows CP-1253 (Greek)
                      04E6H = 1254 = Windows CP-1254 (Turkish)
                      04E7H = 1255 = Windows CP-1255 (Hebrew)
                      04E8H = 1256 = Windows CP-1256 (Arabic)
                      04E9H = 1257 = Windows CP-1257 (Baltic)
                      04EAH = 1258 = Windows CP-1258 (Vietnamese)
                      0551H = 1361 = Windows CP-1361 (Korean (Johab))
                      2710H = 10000 = Apple Roman
                      8000H = 32768 = Apple Roman
                      8001H = 32769 = Windows CP-1252 (Latin I) (BIFF2-BIFF3)
    """
    _REC_ID = 0x0042
    UTF_16 = 0x04B0

    def __init__(self):
        self._rec_data = pack('<H', self.UTF_16)

class Window1Record(BiffRecord):
    """
    Offset Size Contents
    0      2    Horizontal position of the document window (in twips = 1/20 of a point)
    2      2    Vertical position of the document window (in twips = 1/20 of a point)
    4      2    Width of the document window (in twips = 1/20 of a point)
    6      2    Height of the document window (in twips = 1/20 of a point)
    8      2    Option flags:
                  Bits  Mask  Contents
                  0     0001H 0 = Window is visible 1 = Window is hidden
                  1     0002H 0 = Window is open 1 = Window is minimised
                  3     0008H 0 = Horizontal scroll bar hidden 1 = Horizontal scroll bar visible
                  4     0010H 0 = Vertical scroll bar hidden 1 = Vertical scroll bar visible
                  5     0020H 0 = Worksheet tab bar hidden 1 = Worksheet tab bar visible
    10     2    Index to active (displayed) worksheet
    12     2    Index of first visible tab in the worksheet tab bar
    14     2    Number of selected worksheets (highlighted in the worksheet tab bar)
    16     2    Width of worksheet tab bar (in 1/1000 of window width). The remaining space is used by the
                horizontal scrollbar.
    """
    _REC_ID = 0x003D
    # flags

    def __init__(self,
                 hpos_twips, vpos_twips,
                 width_twips, height_twips,
                 flags,
                 active_sheet,
                 first_tab_index, selected_tabs, tab_width):
        self._rec_data = pack('<9H', hpos_twips, vpos_twips,
                                      width_twips, height_twips,
                                      flags,
                                      active_sheet,
                                      first_tab_index, selected_tabs, tab_width)

class FontRecord(BiffRecord):
    """
    WARNING
        The font with index 4 is omitted in all BIFF versions.
        This means the first four fonts have zero-based indexes, and
        the fifth font and all following fonts are referenced with one-based
        indexes.

    Offset Size Contents
    0      2    Height of the font (in twips = 1/20 of a point)
    2      2    Option flags:
                  Bit Mask    Contents
                  0   0001H   1 = Characters are bold (redundant, see below)
                  1   0002H   1 = Characters are italic
                  2   0004H   1 = Characters are underlined (redundant, see below)
                  3   0008H   1 = Characters are struck out
                        0010H 1 = Outline
                        0020H  1 = Shadow
    4     2     Colour index
    6     2     Font weight (100-1000).
                Standard values are 0190H (400) for normal text and 02BCH
                (700) for bold text.
    8     2     Escapement type:
                  0000H = None
                  0001H = Superscript
                  0002H = Subscript
    10    1     Underline type:
                  00H = None
                  01H = Single
                  21H = Single accounting
                  02H = Double
                  22H = Double accounting
    11    1     Font family:
                  00H = None (unknown or don't care)
                  01H = Roman (variable width, serifed)
                  02H = Swiss (variable width, sans-serifed)
                  03H = Modern (fixed width, serifed or sans-serifed)
                  04H = Script (cursive)
                  05H = Decorative (specialised, i.e. Old English, Fraktur)
    12    1     Character set:
                  00H = 0 = ANSI Latin
                  01H = 1 = System default
                  02H = 2 = Symbol
                  4DH = 77 = Apple Roman
                  80H = 128 = ANSI Japanese Shift-JIS
                  81H = 129 = ANSI Korean (Hangul)
                  82H = 130 = ANSI Korean (Johab)
                  86H = 134 = ANSI Chinese Simplified GBK
                  88H = 136 = ANSI Chinese Traditional BIG5
                  A1H = 161 = ANSI Greek
                  A2H = 162 = ANSI Turkish
                  A3H = 163 = ANSI Vietnamese
                  B1H = 177 = ANSI Hebrew
                  B2H = 178 = ANSI Arabic
                  BAH = 186 = ANSI Baltic
                  CCH = 204 = ANSI Cyrillic
                  DEH = 222 = ANSI Thai
                  EEH = 238 = ANSI Latin II (Central European)
                  FFH = 255 = OEM Latin I
    13    1     Not used
    14    var.  Font name:
                  BIFF5/BIFF7: Byte string, 8-bit string length
                  BIFF8: Unicode string, 8-bit string length
    The boldness and underline flags are still set in the options field,
    but not used on reading the font. Font weight and underline type
    are specified in separate fields instead.
    """
    _REC_ID = 0x0031

    def __init__(self,
                    height, options, colour_index, weight, escapement,
                    underline, family, charset,
                    name):
        uname = upack1(name)
        uname_len = len(uname)

        self._rec_data = pack('<5H4B%ds' % uname_len, height, options, colour_index, weight, escapement,
                                                underline, family, charset, 0x00,
                                                uname)

class NumberFormatRecord(BiffRecord):
    """
    Record FORMAT, BIFF8:
    Offset  Size    Contents
    0       2       Format index used in other records
    2       var.    Number format string (Unicode string, 16-bit string length)

    From  BIFF5  on,  the built-in number formats will be omitted. The built-in
    formats  are  dependent  on  the current regional settings of the operating
    system.  The following table shows which number formats are used by default
    in  a  US-English  environment.  All indexes from 0 to 163 are reserved for
    built-in formats. The first user-defined format starts at 164.

    The built-in number formats, BIFF5-BIFF8

    Index   Type        Format string
    0       General     General
    1       Decimal     0
    2       Decimal     0.00
    3       Decimal     #,##0
    4       Decimal     #,##0.00
    5       Currency    "$"#,##0_);("$"#,##
    6       Currency    "$"#,##0_);[Red]("$"#,##
    7       Currency    "$"#,##0.00_);("$"#,##
    8       Currency    "$"#,##0.00_);[Red]("$"#,##
    9       Percent     0%
    10      Percent     0.00%
    11      Scientific  0.00E+00
    12      Fraction    # ?/?
    13      Fraction    # ??/??
    14      Date        M/D/YY
    15      Date        D-MMM-YY
    16      Date        D-MMM
    17      Date        MMM-YY
    18      Time        h:mm AM/PM
    19      Time        h:mm:ss AM/PM
    20      Time        h:mm
    21      Time        h:mm:ss
    22      Date/Time   M/D/YY h:mm
    37      Account     _(#,##0_);(#,##0)
    38      Account     _(#,##0_);[Red](#,##0)
    39      Account     _(#,##0.00_);(#,##0.00)
    40      Account     _(#,##0.00_);[Red](#,##0.00)
    41      Currency    _("$"* #,##0_);_("$"* (#,##0);_("$"* "-"_);_(@_)
    42      Currency    _(* #,##0_);_(* (#,##0);_(* "-"_);_(@_)
    43      Currency    _("$"* #,##0.00_);_("$"* (#,##0.00);_("$"* "-"??_);_(@_)
    44      Currency    _(* #,##0.00_);_(* (#,##0.00);_(* "-"??_);_(@_)
    45      Time        mm:ss
    46      Time        [h]:mm:ss
    47      Time        mm:ss.0
    48      Scientific  ##0.0E+0
    49      Text        @
    """
    _REC_ID = 0x041E

    def __init__(self, idx, fmtstr):
        ufmtstr = upack2(fmtstr)
        ufmtstr_len = len(ufmtstr)

        self._rec_data = pack('<H%ds' % ufmtstr_len, idx, ufmtstr)


class XFRecord(BiffRecord):
    """
    XF Substructures
    -------------------------------------------------------------------------
    XF_TYPE_PROT  XF Type and Cell Protection (3 Bits), BIFF3-BIFF8
    These 3 bits are part of a specific data byte.
    Bit Mask    Contents
    0   01H     1 = Cell is locked
    1   02H     1 = Formula is hidden
    2   04H     0 = Cell XF; 1 = Style XF

    XF_USED_ATTRIB   Attributes   Used  from  Parent  Style  XF  (6  Bits),
    BIFF3-BIFF8  Each  bit  describes  the  validity  of  a  specific group
    of  attributes.  In  cell XFs a cleared bit means the attributes of the
    parent  style XF are used (but only if the attributes are valid there),
    a  set  bit  means  the  attributes  of  this XF are used. In style XFs
    a cleared bit means the attribute setting is valid, a set bit means the
    attribute should be ignored.
    Bit Mask    Contents
    0   01H     Flag for number format
    1   02H     Flag for font
    2   04H     Flag for horizontal and vertical alignment, text wrap, indentation, orientation, rotation, and
                text direction
    3   08H     Flag for border lines
    4   10H     Flag for background area style
    5   20H     Flag for cell protection (cell locked and formula hidden)

    XF_HOR_ALIGN  Horizontal Alignment (3 Bits), BIFF2-BIFF8 The horizontal
    alignment consists of 3 bits and is part of a specific data byte.
    Value   Horizontal alignment
    00H     General
    01H     Left
    02H     Centred
    03H     Right
    04H     Filled
    05H     Justified (BIFF4-BIFF8X)
    06H     Centred across selection (BIFF4-BIFF8X)
    07H     Distributed (BIFF8X)

    XF_VERT_ALIGN Vertical Alignment (2 or 3 Bits), BIFF4-BIFF8
    The vertical alignment consists of 2 bits (BIFF4) or 3 bits (BIFF5-BIFF8)
    and is part of a specific data byte. Vertical alignment is not available
    in BIFF2 and BIFF3.
    Value   Vertical alignment
    00H     Top
    01H     Centred
    02H     Bottom
    03H     Justified (BIFF5-BIFF8X)
    04H     Distributed (BIFF8X)

    XF_ORIENTATION  Text  Orientation  (2  Bits),  BIFF4-BIFF7  In the BIFF
    versions  BIFF4-BIFF7,  text  can  be  rotated  in  steps of 90 degrees
    or  stacked.  The  orientation  mode  consists of 2 bits and is part of
    a specific data byte. In BIFF8 a rotation angle occurs instead of these
    flags.
    Value   Text orientation
    00H     Not rotated
    01H     Letters are stacked top-to-bottom, but not rotated
    02H     Text is rotated 90 degrees counterclockwise
    03H     Text is rotated 90 degrees clockwise

    XF_ROTATION Text Rotation Angle (1 Byte), BIFF8
    Value   Text rotation
    0       Not rotated
    1-90    1 to 90 degrees counterclockwise
    91-180  1 to 90 degrees clockwise
    255     Letters are stacked top-to-bottom, but not rotated

    XF_BORDER_34  Cell  Border  Style  (4  Bytes), BIFF3-BIFF4 Cell borders
    contain a line style and a line colour for each line of the border.
    Bit     Mask        Contents
    2-0     00000007H   Top line style
    7-3     000000F8H   Colour index for top line colour
    10-8    00000700H   Left line style
    15-11   0000F800H   Colour index for left line colour
    18-16   00070000H   Bottom line style
    23-19   00F80000H   Colour index for bottom line colour
    26-24   07000000H   Right line style
    31-27   F8000000H   Colour index for right line colour

    XF_AREA_34  Cell  Background  Area  Style (2 Bytes), BIFF3-BIFF4 A cell
    background  area  style  contains  an area pattern and a foreground and
    background colour.
    Bit     Mask    Contents
    5-0     003FH   Fill pattern
    10-6    07C0H   Colour index for pattern colour
    15-11   F800H   Colour index for pattern background
 ---------------------------------------------------------------------------------------------
    Record XF, BIFF8:
    Offset      Size    Contents
    0           2       Index to FONT record
    2           2       Index to FORMAT record
    4           2       Bit     Mask    Contents
                        2-0     0007H   XF_TYPE_PROT . XF type, cell protection (see above)
                        15-4    FFF0H   Index to parent style XF (always FFFH in style XFs)
    6           1       Bit     Mask    Contents
                        2-0     07H     XF_HOR_ALIGN . Horizontal alignment (see above)
                        3       08H     1 = Text is wrapped at right border
                        6-4     70H     XF_VERT_ALIGN . Vertical alignment (see above)
    7           1       XF_ROTATION: Text rotation angle (see above)
    8           1       Bit     Mask    Contents
                        3-0     0FH     Indent level
                        4       10H     1 = Shrink content to fit into cell
                        5               merge
                        7-6     C0H     Text direction (BIFF8X only)
                                        00b = According to context
                                        01b = Left-to-right
                                        10b = Right-to-left
    9           1       Bit     Mask    Contents
                        7-2     FCH     XF_USED_ATTRIB . Used attributes (see above)
    10          4       Cell border lines and background area:
                        Bit     Mask      Contents
                        3-0     0000000FH Left line style
                        7-4     000000F0H Right line style
                        11-8    00000F00H Top line style
                        15-12   0000F000H Bottom line style
                        22-16   007F0000H Colour index for left line colour
                        29-23   3F800000H Colour index for right line colour
                        30      40000000H 1 = Diagonal line from top left to right bottom
                        31      80000000H 1 = Diagonal line from bottom left to right top
    14          4       Bit     Mask      Contents
                        6-0     0000007FH Colour index for top line colour
                        13-7    00003F80H Colour index for bottom line colour
                        20-14   001FC000H Colour index for diagonal line colour
                        24-21   01E00000H Diagonal line style
                        31-26   FC000000H Fill pattern
    18          2       Bit     Mask    Contents
                        6-0     007FH   Colour index for pattern colour
                        13-7    3F80H   Colour index for pattern background

    """
    _REC_ID = 0x00E0

    def __init__(self, xf, xftype='cell'):
        font_xf_idx, fmt_str_xf_idx, alignment, borders, pattern, protection = xf
        fnt = pack('<H', font_xf_idx)
        fmt = pack('<H', fmt_str_xf_idx)
        if xftype == 'cell':
            prt = pack('<H',
                ((protection.cell_locked    & 0x01) << 0) |
                ((protection.formula_hidden & 0x01) << 1)
            )
        else:
            prt = pack('<H', 0xFFF5)
        aln = pack('B',
            ((alignment.horz & 0x07) << 0) |
            ((alignment.wrap & 0x01) << 3) |
            ((alignment.vert & 0x07) << 4)
        )
        rot = pack('B', alignment.rota)
        txt = pack('B',
            ((alignment.inde & 0x0F) << 0) |
            ((alignment.shri & 0x01) << 4) |
            ((alignment.merg & 0x01) << 5) |
            ((alignment.dire & 0x03) << 6)
        )
        if xftype == 'cell':
            used_attr = pack('B', 0xF8)
        else:
            used_attr = pack('B', 0xF4)

        if borders.left == borders.NO_LINE:
            borders.left_colour = 0x00
        if borders.right == borders.NO_LINE:
            borders.right_colour = 0x00
        if borders.top == borders.NO_LINE:
            borders.top_colour = 0x00
        if borders.bottom == borders.NO_LINE:
            borders.bottom_colour = 0x00
        if borders.diag == borders.NO_LINE:
            borders.diag_colour = 0x00
        brd1 = pack('<L',
            ((borders.left          & 0x0F) << 0 ) |
            ((borders.right         & 0x0F) << 4 ) |
            ((borders.top           & 0x0F) << 8 ) |
            ((borders.bottom        & 0x0F) << 12) |
            ((borders.left_colour   & 0x7F) << 16) |
            ((borders.right_colour  & 0x7F) << 23) |
            ((borders.need_diag1    & 0x01) << 30) |
            ((borders.need_diag2    & 0x01) << 31)
        )
        brd2 = pack('<L',
            ((borders.top_colour    & 0x7F) << 0 ) |
            ((borders.bottom_colour & 0x7F) << 7 ) |
            ((borders.diag_colour   & 0x7F) << 14) |
            ((borders.diag          & 0x0F) << 21) |
            ((pattern.pattern       & 0x3F) << 26)
        )
        pat = pack('<H',
            ((pattern.pattern_fore_colour & 0x7F) << 0 ) |
            ((pattern.pattern_back_colour & 0x7F) << 7 )
        )
        self._rec_data = fnt + fmt + prt + \
                        aln + rot + txt + used_attr + \
                        brd1 + brd2 + \
                        pat

class StyleRecord(BiffRecord):
    """
    STYLE record for user-defined cell styles, BIFF3-BIFF8:
    Offset  Size    Contents
    0       2       Bit     Mask    Contents
                    11-0    0FFFH   Index to style XF record
                    15      8000H   Always 0 for user-defined styles
    2       var.    BIFF2-BIFF7: Non-empty byte string, 8-bit string length
                    BIFF8: Non-empty Unicode string, 16-bit string length
    STYLE record for built-in cell styles, BIFF3-BIFF8:
    Offset  Size    Contents
    0       2       Bit     Mask    Contents
                    11-0    0FFFH   Index to style XF record
                    15      8000H   Always 1 for built-in styles
    2       1       Identifier of the built-in cell style:
                        00H = Normal
                        01H = RowLevel_lv (see next field)
                        02H = ColLevel_lv (see next field)
                        03H = Comma
                        04H = Currency
                        05H = Percent
                        06H = Comma [0] (BIFF4-BIFF8)
                        07H = Currency [0] (BIFF4-BIFF8)
                        08H = Hyperlink (BIFF8)
                        09H = Followed Hyperlink (BIFF8)
    3       1       Level for RowLevel or ColLevel style
                    (zero-based, lv), FFH otherwise
    The  RowLevel  and  ColLevel  styles specify the formatting of subtotal
    cells  in  a specific outline level. The level is specified by the last
    field  in the STYLE record. Valid values are 0-6 for the outline levels
    1-7.
    """
    _REC_ID = 0x0293

    def __init__(self):
        self._rec_data = pack('<HBB', 0x8000, 0x00, 0xFF)
        # TODO: implement user-defined styles???


class PaletteRecord(BiffRecord):
    """
    This  record  contains  the  definition  of  all  user-defined  colours
    available for cell and object formatting.

    Record PALETTE, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Number of following colours (nm). Contains 16 in BIFF3-BIFF4 and 56 in BIFF5-BIFF8.
    2       4*nm    List of nm RGB colours

    The following table shows how colour indexes are used in other records:

    Colour index    Resulting colour or internal list index
    00H             Built-in Black (R = 00H, G = 00H, B = 00H)
    01H             Built-in White (R = FFH, G = FFH, B = FFH)
    02H             Built-in Red (R = FFH, G = 00H, B = 00H)
    03H             Built-in Green (R = 00H, G = FFH, B = 00H)
    04H             Built-in Blue (R = 00H, G = 00H, B = FFH)
    05H             Built-in Yellow (R = FFH, G = FFH, B = 00H)
    06H             Built-in Magenta (R = FFH, G = 00H, B = FFH)
    07H             Built-in Cyan (R = 00H, G = FFH, B = FFH)
    08H             First user-defined colour from the PALETTE record (entry 0 from record colour list)
    .........................

    17H (BIFF3-BIFF4) Last user-defined colour from the PALETTE record (entry 15 or 55 from record colour list)
    3FH (BIFF5-BIFF8)

    18H (BIFF3-BIFF4) System window text colour for border lines (used in records XF, CF, and
    40H (BIFF5-BIFF8) WINDOW2 (BIFF8 only))

    19H (BIFF3-BIFF4) System window background colour for pattern background (used in records XF, and CF)
    41H (BIFF5-BIFF8)

    43H             System face colour (dialogue background colour)
    4DH             System window text colour for chart border lines
    4EH             System window background colour for chart areas
    4FH             Automatic colour for chart border lines (seems to be always Black)
    50H             System ToolTip background colour (used in note objects)
    51H             System ToolTip text colour (used in note objects)
    7FFFH           System window text colour for fonts (used in records FONT, EFONT, and CF)

    """
    _REC_ID = 0x0092

    def __init__(self, custom_palette):
        n_colours = len(custom_palette)
        assert n_colours == 56
        # Pack number of colors with little-endian, what xlrd and excel expect.
        self._rec_data = pack('<H', n_colours)
        # Microsoft lists colors in big-endian format with 24 bits/color.
        # Pad LSB of each color with 0x00, and write out in big-endian.
        fmt = '>%dI' % n_colours
        self._rec_data += pack(fmt, *(custom_palette))

class BoundSheetRecord(BiffRecord):
    """
    This  record  is  located  in  the workbook globals area and represents
    a  sheet  inside  of  the  workbook. For each sheet a BOUNDSHEET record
    is  written.  It  stores  the sheet name and a stream offset to the BOF
    record    within   the   workbook   stream.  The  record  is also known
    as BUNDLESHEET.

    Record BOUNDSHEET, BIFF5-BIFF8:
    Offset  Size    Contents
    0       4       Absolute stream position of the BOF record of the sheet represented by this record. This
                    field is never encrypted in protected files.
    4       1       Visibility:
                        00H = Visible
                        01H = Hidden
                        02H = Strong hidden
    5       1       Sheet type:
                        00H = Worksheet
                        02H = Chart
                        06H = Visual Basic module
    6       var.    Sheet name:
                        BIFF5/BIFF7: Byte string, 8-bit string length
                        BIFF8: Unicode string, 8-bit string length
    """
    _REC_ID = 0x0085

    def __init__(self, stream_pos, visibility, sheetname, encoding='ascii'):
        usheetname = upack1(sheetname, encoding)
        uusheetname_len = len(usheetname)

        self._rec_data = pack('<LBB%ds' % uusheetname_len, stream_pos, visibility, 0x00, usheetname)


class ContinueRecord(BiffRecord):
    """
    Whenever  the content of a record exceeds the given limits (see table),
    the  record  must  be  split.  Several  CONTINUE records containing the
    additional data are added after the parent record.

    BIFF version    Maximum data size of a record
    BIFF2-BIFF7     2080 bytes (2084 bytes including record header)
    BIFF8           8224 bytes (8228 bytes including record header) (0x2020)

    Record CONTINUE, BIFF2-BIFF8:
    Offset  Size    Contents
    0       var.    Data continuation of the previous record

    Unicode  strings  are  split in a special way. At the beginning of each
    CONTINUE  record  the option flags byte is repeated. Only the character
    size  flag  will  be set in this flags byte, the Rich-Text flag and the
    Far-East  flag  are set to zero. In each CONTINUE record it is possible
    that  the  character  size  changes  from  8-bit  characters  to 16-bit
    characters and vice versa.

    Never  a  Unicode  string  is  split  until  and  including  the  first
    character.  That means, all header fields (string length, option flags,
    optional Rich-Text size, and optional Far-East data size) and the first
    character  of  the string have to occur together in the leading record,
    or  have  to  be  moved completely into the CONTINUE record. Formatting
    runs cannot be split between their components (character index and FONT
    record  index).  If  a string is split between two formatting runs, the
    option flags field will not be repeated in the CONTINUE record.
    """
    _REC_ID = 0x003C


class SSTRecord(BiffRecord):
    """
    This  record  contains  a  list  of  all  strings  used anywhere in the
    workbook.  Each string occurs only once. The workbook uses indexes into
    the list to reference the strings.

    Record SST, BIFF8:
    Offset  Size    Contents
    0       4       Total number of strings in the workbook (see below)
    4       4       Number of following strings (nm)
    8       var.    List of nm Unicode strings, 16-bit string length

    The  first  field  of  the  SST  record  counts  the  total  occurrence
    of  strings  in  the  workbook.  For  instance,  the string AAA is used
    3  times  and  the string BBB is used 2 times. The first field contains
    5 and the second field contains 2, followed by the two strings.
    """
    _REC_ID = 0x00FC


class ExtSSTRecord(BiffRecord):
    """
    This  record  occurs  in  conjunction  with  the SST record. It is used
    by  Excel  to create a hash table with stream offsets to the SST record
    to optimise string search operations. Excel may not shorten this record
    if  strings  are deleted from the shared string table, so the last part
    might  contain  invalid  data. The stream indexes in this record divide
    the SST into portions containing a constant number of strings.

    Record EXTSST, BIFF8:

    Offset  Size    Contents
    0       2       Number of strings in a portion, this number is >=8
    2       var.    List of OFFSET structures for all portions. Each OFFSET contains the following data:
                        Offset Size Contents
                        0       4   Absolute stream position of first string of the portion
                        4       2   Position of first string of the portion inside of current record,
                                    including record header. This counter restarts at zero, if the SST
                                    record is continued with a CONTINUE record.
                        6       2   Not used
    """
    _REC_ID = 0x00FF

    def __init__(self, sst_stream_pos, str_placement, portions_len):
        extsst = {}
        abs_stream_pos = sst_stream_pos
        str_counter = 0
        portion_counter = 0
        while str_counter < len(str_placement):
            str_chunk_num, pos_in_chunk = str_placement[str_counter]
            if str_chunk_num != portion_counter:
                portion_counter = str_chunk_num
                abs_stream_pos += portions_len[portion_counter-1]
                #print hex(abs_stream_pos)
            str_stream_pos = abs_stream_pos + pos_in_chunk + 4 # header
            extsst[str_counter] = (pos_in_chunk, str_stream_pos)
            str_counter += 1

        exsst_str_count_delta = max(8, len(str_placement)*8/0x2000) # maybe smth else?
        self._rec_data = pack('<H', exsst_str_count_delta)
        str_counter = 0
        while str_counter < len(str_placement):
            self._rec_data += pack('<IHH', extsst[str_counter][1], extsst[str_counter][0], 0)
            str_counter += exsst_str_count_delta

class DimensionsRecord(BiffRecord):
    """
    Record DIMENSIONS, BIFF8:

    Offset  Size    Contents
    0       4       Index to first used row
    4       4       Index to last used row, increased by 1
    8       2       Index to first used column
    10      2       Index to last used column, increased by 1
    12      2       Not used
    """
    _REC_ID = 0x0200
    def __init__(self, first_used_row, last_used_row, first_used_col, last_used_col):
        if first_used_row > last_used_row or first_used_col > last_used_col:
            # Special case: empty worksheet
            first_used_row = first_used_col = 0
            last_used_row = last_used_col = -1
        self._rec_data = pack('<2L3H',
            first_used_row, last_used_row + 1,
            first_used_col, last_used_col + 1,
            0x00)


class Window2Record(BiffRecord):
    """
    Record WINDOW2, BIFF8:

    Offset  Size Contents
    0       2 Option flags (see below)
    2       2 Index to first visible row
    4       2 Index to first visible column
    6       2 Colour index of grid line colour. Note that in BIFF2-BIFF7 an RGB colour is
                written instead.
    8       2 Not used
    10      2 Cached magnification factor in page break preview (in percent); 0 = Default (60%)
    12      2 Cached magnification factor in normal view (in percent); 0 = Default (100%)
    14      4 Not used

    In  BIFF8  this record stores used magnification factors for page break
    preview  and  normal  view.  These  values  are  used  to  restore  the
    magnification,  when the view is changed. The real magnification of the
    currently  active  view  is  stored  in the SCL record. The type of the
    active view is stored in the option flags field (see below).

     0 0001H 0 = Show formula results 1 = Show formulas
     1 0002H 0 = Do not show grid lines 1 = Show grid lines
     2 0004H 0 = Do not show sheet headers 1 = Show sheet headers
     3 0008H 0 = Panes are not frozen 1 = Panes are frozen (freeze)
     4 0010H 0 = Show zero values as empty cells 1 = Show zero values
     5 0020H 0 = Manual grid line colour 1 = Automatic grid line colour
     6 0040H 0 = Columns from left to right 1 = Columns from right to left
     7 0080H 0 = Do not show outline symbols 1 = Show outline symbols
     8 0100H 0 = Keep splits if pane freeze is removed 1 = Remove splits if pane freeze is removed
     9 0200H 0 = Sheet not selected 1 = Sheet selected (BIFF5-BIFF8)
    10 0400H 0 = Sheet not visible 1 = Sheet visible (BIFF5-BIFF8)
    11 0800H 0 = Show in normal view 1 = Show in page break preview (BIFF8)

    The freeze flag specifies, if a following PANE record describes unfrozen or frozen panes.

    *** This class appends the optional SCL record ***

    Record SCL, BIFF4-BIFF8:

    This record stores the magnification of the active view of the current worksheet.
    In BIFF8 this can be either the normal view or the page break preview.
    This is determined in the WINDOW2 record. The SCL record is part of the
    Sheet View Settings Block.

    Offset  Size    Contents
    0       2       Numerator of the view magnification fraction (num)
    2       2       Denumerator [denominator] of the view magnification fraction (den)
    The magnification is stored as reduced fraction. The magnification results from num/den.

    SJM note: Excel expresses (e.g.) 25% in reduced form i.e. 1/4. Reason unknown. This code
    writes 25/100, and Excel is happy with that.

    """
    _REC_ID = 0x023E

    def __init__(self, options, first_visible_row, first_visible_col,
        grid_colour, preview_magn, normal_magn, scl_magn):
        self._rec_data = pack('<7HL', options,
                                    first_visible_row, first_visible_col,
                                    grid_colour,
                                    0x00,
                                    preview_magn, normal_magn,
                                    0x00)
        if scl_magn is not None:
            self._scl_rec = pack('<4H', 0x00A0, 4, scl_magn, 100)
        else:
            self._scl_rec = b''

    def get(self):
        return self.get_rec_header() + self._rec_data + self._scl_rec


class PanesRecord(BiffRecord):
    """
    This record stores the position of window panes. It is part of the Sheet
    View Settings Block. If the sheet does not contain any splits, this
    record will not occur.
    A sheet can be split in two different ways, with unfrozen panes or with
    frozen panes. A flag in the WINDOW2 record specifies, if the panes are
    frozen, which affects the contents of this record.

    Record PANE, BIFF2-BIFF8:
    Offset      Size        Contents
    0           2           Position of the vertical split
                            (px, 0 = No vertical split):
                            Unfrozen pane: Width of the left pane(s)
                            (in twips = 1/20 of a point)
                            Frozen pane: Number of visible
                            columns in left pane(s)
    2           2           Position of the horizontal split
                            (py, 0 = No horizontal split):
                            Unfrozen pane: Height of the top pane(s)
                            (in twips = 1/20 of a point)
                            Frozen pane: Number of visible
                            rows in top pane(s)
    4           2           Index to first visible row
                            in bottom pane(s)
    6           2           Index to first visible column
                            in right pane(s)
    8           1           Identifier of pane with active
                            cell cursor
    [9]         1           Not used (BIFF5-BIFF8 only, not written
                            in BIFF2-BIFF4)

    If the panes are frozen, pane 0 is always active, regardless
    of the cursor position. The correct identifiers for all possible
    combinations of visible panes are shown in the following pictures.

    px = 0, py = 0                  px = 0, py > 0
    --------------------------      ------------|-------------
    |                        |      |                        |
    |                        |      |           3            |
    |                        |      |                        |
    -           3            -      --------------------------
    |                        |      |                        |
    |                        |      |           2            |
    |                        |      |                        |
    --------------------------      ------------|-------------

    px > 0, py = 0                  px > 0, py > 0
    ------------|-------------      ------------|-------------
    |           |            |      |           |            |
    |           |            |      |     3     |      2     |
    |           |            |      |           |            |
    -     3     |      1     -      --------------------------
    |           |            |      |           |            |
    |           |            |      |     1     |      0     |
    |           |            |      |           |            |
    ------------|-------------      ------------|-------------
    """
    _REC_ID = 0x0041
    
    valid_active_pane = {
        # entries are of the form:
        # (int(px > 0),int(px>0)) -> allowed values
        (0,0):(3,),
        (0,1):(2,3),
        (1,0):(1,3),
        (1,1):(0,1,2,3),
        }
    
    def __init__(self, px, py, first_row_bottom, first_col_right, active_pane):
        allowed = self.valid_active_pane.get(
            (int(px > 0),int(py > 0))
            )
        if active_pane not in allowed:
            raise ValueError('Cannot set active_pane to %i, must be one of %s' % (
                    active_pane, ', '.join(allowed)
                    ))
        self._rec_data = pack('<5H',
                              px, py,
                              first_row_bottom, first_col_right,
                              active_pane)


class RowRecord(BiffRecord):
    """
    This  record  contains  the properties of a single row in a sheet. Rows
    and cells in a sheet are divided into blocks of 32 rows.

    Record ROW, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Index of this row
    2       2       Index to column of the first cell which is described by a cell record
    4       2       Index to column of the last cell which is described by a cell record,
                    increased by 1
    6       2       Bit     Mask    Contents
                    14-0    7FFFH   Height of the row, in twips = 1/20 of a point
                    15      8000H   0 = Row has custom height; 1 = Row has default height
    8       2       Not used
    10      2       In BIFF3-BIFF4 this field contains a relative offset
                    to calculate stream position of the first cell record
                    for this row. In BIFF5-BIFF8 this field is not used
                    anymore, but the DBCELL record instead.
    12      4       Option flags and default row formatting:
                    Bit     Mask        Contents
                    2-0     00000007H   Outline level of the row
                    4       00000010H   1 = Outline group starts or ends here (depending
                                        on where the outline buttons are located,
                                        see WSBOOL record), and is collapsed
                    5       00000020H   1 = Row is hidden (manually, or by a filter or outline group)
                    6       00000040H   1 = Row height and default font height do not match
                    7       00000080H   1 = Row has explicit default format (fl)
                    8       00000100H   Always 1
                    27-16   0FFF0000H   If fl=1: Index to default XF record
                    28      10000000H   1 = Additional space above the row. This flag is set,
                                        if the upper border of at least one cell in this row
                                        or if the lower border of at least one cell in the row
                                        above is formatted with a thick line style.
                                        Thin and medium line styles are not taken into account.
                    29      20000000H   1 = Additional space below the row. This flag is set,
                                        if the lower border of at least one cell in this row
                                        or if the upper border of at least one cell in the row
                                        below is formatted with a medium or thick line style.
                                        Thin line styles are not taken into account.
    """

    _REC_ID = 0x0208

    def __init__(self, index, first_col, last_col, height_options, options):
        self._rec_data = pack('<6HL', index, first_col, last_col + 1,
                                        height_options,
                                        0x00, 0x00,
                                        options)

class LabelSSTRecord(BiffRecord):
    """
    This record represents a cell that contains a string. It replaces the
    LABEL record and RSTRING record used in BIFF2-BIFF7.
    """
    _REC_ID = 0x00FD

    def __init__(self, row, col, xf_idx, sst_idx):
        self._rec_data = pack('<3HL', row, col, xf_idx, sst_idx)


class MergedCellsRecord(BiffRecord):
    """
    This record contains all merged cell ranges of the current sheet.

    Record MERGEDCELLS, BIFF8:

    Offset  Size    Contents
    0       var.    Cell range address list with all merged ranges

    ------------------------------------------------------------------

    A cell range address list consists of a field with the number of ranges
    and the list of the range addresses.

    Cell range address list, BIFF8:

    Offset  Size            Contents
    0       2               Number of following cell range addresses (nm)
    2       8*nm            List of nm cell range addresses

    ---------------------------------------------------------------------
    Cell range address, BIFF8:

    Offset  Size    Contents
    0       2       Index to first row
    2       2       Index to last row
    4       2       Index to first column
    6       2       Index to last column

    """
    _REC_ID = 0x00E5

    def __init__(self, merged_list):
        i = len(merged_list) - 1
        while i >= 0:
            j = 0
            merged = b''
            while (i >= 0) and (j < 0x403):
                r1, r2, c1, c2 = merged_list[i]
                merged += pack('<4H', r1, r2, c1, c2)
                i -= 1
                j += 1
            self._rec_data += pack('<3H', self._REC_ID, len(merged) + 2, j) + \
                                    merged

    # for some reason Excel doesn't use CONTINUE
    def get(self):
        return self._rec_data

class MulBlankRecord(BiffRecord):
    """
    This  record  represents  a  cell  range  of empty cells. All cells are
    located in the same row.

    Record MULBLANK, BIFF5-BIFF8:

    Offset  Size    Contents
    0       2       Index to row
    2       2       Index to first column (fc)
    4       2*nc    List of nc=lc-fc+1 16-bit indexes to XF records
    4+2*nc  2       Index to last column (lc)
    """
    _REC_ID = 0x00BE

    def __init__(self, row, first_col, last_col, xf_index):
        blanks_count = last_col-first_col+1
        self._rec_data = pack('<%dH' % blanks_count, *([xf_index] * blanks_count))
        self._rec_data = pack('<2H', row, first_col) +  self._rec_data + pack('<H',  last_col)


class BlankRecord(BiffRecord):
    """
    This  record  represents  an empty cell.

    Record BLANK, BIFF5-BIFF8:

    Offset  Size    Contents
    0       2       Index to row
    2       2       Index to first column (fc)
    4       2       indexes to XF record
    """
    _REC_ID = 0x0201

    def __init__(self, row, col, xf_index):
        self._rec_data = pack('<3H', row, col, xf_index)


class RKRecord(BiffRecord):
    """
    This record represents a cell that contains an RK value (encoded integer or
    floating-point value). If a floating-point value cannot be encoded to an RK value,
    a NUMBER record will be written.
    """
    _REC_ID = 0x027E

    def __init__(self, row, col, xf_index, rk_encoded):
        self._rec_data = pack('<3Hi', row, col, xf_index, rk_encoded)


class NumberRecord(BiffRecord):
    """
    This record represents a cell that contains an IEEE-754 floating-point value.
    """
    _REC_ID = 0x0203

    def __init__(self, row, col, xf_index, number):
        self._rec_data = pack('<3Hd', row, col, xf_index, number)

class BoolErrRecord(BiffRecord):
    """
    This record represents a cell that contains a boolean or error value.
    """
    _REC_ID = 0x0205

    def __init__(self, row, col, xf_index, number, is_error):
        self._rec_data = pack('<3HBB', row, col, xf_index, number, is_error)


class FormulaRecord(BiffRecord):
    """
    Offset Size Contents
    0      2    Index to row
    2      2    Index to column
    4      2    Index to XF record
    6      8    Result of the formula
    14     2    Option flags:
                Bit Mask    Contents
                0   0001H   1 = Recalculate always
                1   0002H   1 = Calculate on open
                3   0008H   1 = Part of a shared formula
    16     4    Not used
    20     var. Formula data (RPN token array)

    """
    _REC_ID = 0x0006

    def __init__(self, row, col, xf_index, rpn, calc_flags=0):
        self._rec_data = pack('<3HQHL', row, col, xf_index, 0xFFFF000000000003, calc_flags & 3, 0) + rpn


class GutsRecord(BiffRecord):
    """
    This record contains information about the layout of outline symbols.

    Record GUTS, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Width of the area to display row outlines (left of the sheet), in pixel
    2       2       Height of the area to display column outlines (above the sheet), in pixel
    4       2       Number of visible row outline levels (used row levels + 1; or 0, if not used)
    6       2       Number of visible column outline levels (used column levels + 1; or 0, if not used)

    """

    _REC_ID = 0x0080

    def __init__(self, row_gut_width, col_gut_height, row_visible_levels, col_visible_levels):
        self._rec_data = pack('<4H', row_gut_width, col_gut_height, row_visible_levels, col_visible_levels)

class WSBoolRecord(BiffRecord):
    """
    This  record stores a 16 bit value with Boolean options for the current
    sheet.  From BIFF5 on the "Save external linked values" option is moved
    to the record BOOKBOOL.

    Option flags of record WSBOOL, BIFF3-BIFF8:

    Bit     Mask    Contents
    0       0001H   0 = Do not show automatic page breaks
                    1 = Show automatic page breaks
    4       0010H   0 = Standard sheet
                    1 = Dialogue sheet (BIFF5-BIFF8)
    5       0020H   0 = No automatic styles in outlines
                    1 = Apply automatic styles to outlines
    6       0040H   0 = Outline buttons above outline group
                    1 = Outline buttons below outline group
    7       0080H   0 = Outline buttons left of outline group
                    1 = Outline buttons right of outline group
    8       0100H   0 = Scale printout in percent
                    1 = Fit printout to number of pages
    9       0200H   0 = Save external linked values (BIFF3?BIFF4 only)
                    1 = Do not save external linked values (BIFF3?BIFF4 only)
    10      0400H   0 = Do not show row outline symbols
                    1 = Show row outline symbols
    11      0800H   0 = Do not show column outline symbols
                    1 = Show column outline symbols
    13-12   3000H   These flags specify the arrangement of windows.
                    They are stored in BIFF4 only.
                    00 = Arrange windows tiled
                    01 = Arrange windows horizontal
                    10 = Arrange windows vertical112 = Arrange windows cascaded
    The following flags are valid for BIFF4-BIFF8 only:
    14      4000H   0 = Standard expression evaluation
                    1 = Alternative expression evaluation
    15      8000H   0 = Standard formula entries
                    1 = Alternative formula entries

    """
    _REC_ID = 0x0081

    def __init__(self, options):
        self._rec_data = pack('<H', options)

class ColInfoRecord(BiffRecord):
    """
    This record specifies the width for a given range of columns.
    If a column does not have a corresponding COLINFO record,
    the width specified in the record STANDARDWIDTH is used. If
    this record is also not present, the contents of the record
    DEFCOLWIDTH is used instead.
    This record also specifies a default XF record to use for
    cells in the columns that are not described by any cell record
    (which contain the XF index for that cell). Additionally,
    the option flags field contains hidden, outline, and collapsed
    options applied at the columns.

    Record COLINFO, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Index to first column in the range
    2       2       Index to last column in the range
    4       2       Width of the columns in 1/256 of the width of the zero character, using default font
                    (first FONT record in the file)
    6       2       Index to XF record for default column formatting
    8       2       Option flags:
                    Bits    Mask    Contents
                    0       0001H   1 = Columns are hidden
                    10-8    0700H   Outline level of the columns (0 = no outline)
                    12      1000H   1 = Columns are collapsed
    10      2       Not used

    """
    _REC_ID = 0x007D

    def __init__(self, first_col, last_col, width, xf_index, options, unused):
        self._rec_data = pack('<6H', first_col, last_col, width, xf_index, options, unused)

class CalcModeRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block.
    It specifies whether to calculate formulas manually,
    automatically or automatically except for multiple table operations.

    Record CALCMODE, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       FFFFH = automatic except for multiple table operations
                    0000H = manually
                    0001H = automatically (default)
    """
    _REC_ID = 0x000D

    def __init__(self, calc_mode):
        self._rec_data = pack('<h', calc_mode)


class CalcCountRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block. It specifies the maximum
    number of times the formulas should be iteratively calculated. This is a fail-safe
    against mutually recursive formulas locking up a spreadsheet application.

    Record CALCCOUNT, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       Maximum number of iterations allowed in circular references
    """

    _REC_ID = 0x000C

    def __init__(self, calc_count):
        self._rec_data = pack('<H', calc_count)

class RefModeRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block.
    It stores which method is used to show cell addresses in formulas.
    The “RC” mode uses numeric indexes for rows and columns,
    i.e. “R(1)C(-1)”, or “R1C1:R2C2”.
    The “A1” mode uses characters for columns and numbers for rows,
    i.e. “B1”, or “$A$1:$B$2”.

    Record REFMODE, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = RC mode; 1 = A1 mode

    """
    _REC_ID = 0x00F

    def __init__(self, ref_mode):
        self._rec_data = pack('<H', ref_mode)

class IterationRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block.
    It stores if iterations are allowed while calculating recursive formulas.

    Record ITERATION, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = Iterations off; 1 = Iterations on
    """
    _REC_ID = 0x011

    def __init__(self, iterations_on):
        self._rec_data = pack('<H', iterations_on)

class DeltaRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block.
    It stores the maximum change of the result to exit an iteration.

    Record DELTA, BIFF2-BIFF8:

    Offset  Size    Contents
    0       8       Maximum change in iteration
                    (IEEE 754 floating-point value,
                     64bit double precision)
    """
    _REC_ID = 0x010

    def __init__(self, delta):
        self._rec_data = pack('<d', delta)

class SaveRecalcRecord(BiffRecord):
    """
    This record is part of the Calculation Settings Block.
    It contains the “Recalculate before save” option in
    Excel's calculation settings dialogue.

    Record SAVERECALC, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       0 = Do not recalculate;
                    1 = Recalculate before saving the document

    """
    _REC_ID = 0x05F

    def __init__(self, recalc):
        self._rec_data = pack('<H', recalc)

class PrintHeadersRecord(BiffRecord):
    """
    This record stores if the row and column headers
    (the areas with row numbers and column letters) will be printed.

    Record PRINTHEADERS, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = Do not print row/column headers;
                    1 = Print row/column headers
    """
    _REC_ID = 0x02A

    def __init__(self, print_headers):
        self._rec_data = pack('<H', print_headers)


class PrintGridLinesRecord(BiffRecord):
    """
    This record stores if sheet grid lines will be printed.

    Record PRINTGRIDLINES, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       0 = Do not print sheet grid lines;
                    1 = Print sheet grid lines

    """
    _REC_ID = 0x02B

    def __init__(self, print_grid):
        self._rec_data = pack('<H', print_grid)


class GridSetRecord(BiffRecord):
    """
    This record specifies if the option to print sheet grid lines
    (record PRINTGRIDLINES) has ever been changed.

    Record GRIDSET, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       0 = Print grid lines option never changed
                    1 = Print grid lines option changed
    """
    _REC_ID = 0x082

    def __init__(self, print_grid_changed):
        self._rec_data = pack('<H', print_grid_changed)


class DefaultRowHeightRecord(BiffRecord):
    """
    This record specifies the default height and default flags
    for rows that do not have a corresponding ROW record.

    Record DEFAULTROWHEIGHT, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       Option flags:
                    Bit Mask    Contents
                    0   0001H   1 = Row height and default font height do not match
                    1   0002H   1 = Row is hidden
                    2   0004H   1 = Additional space above the row
                    3   0008H   1 = Additional space below the row
    2       2       Default height for unused rows, in twips = 1/20 of a point

    """
    _REC_ID = 0x0225

    def __init__(self, options, def_height):
        self._rec_data = pack('<2H', options, def_height)


class DefColWidthRecord(BiffRecord):
    """
    This record specifies the default column width for columns that
    do not have a specific width set using the record COLINFO or COLWIDTH.
    This record has no effect, if a STANDARDWIDTH record is present in the file.

    Record DEFCOLWIDTH, BIFF2-BIFF8:

    Offset  Size    Contents
    0       2       Column width in characters, using the width of the zero
                    character from default font (first FONT record in the file)
    """
    _REC_ID = 0x0055

    def __init__(self, def_width):
        self._rec_data = pack('<H', options, def_width)

class HorizontalPageBreaksRecord(BiffRecord):
    """
    This  record  is  part  of  the  Page  Settings  Block. It contains all
    horizontal manual page breaks.

    Record HORIZONTALPAGEBREAKS, BIFF8:
    Offset  Size  Contents
    0       2     Number of following row index structures (nm)
    2       6nm   List of nm row index structures. Each row index
                  structure contains:
                    Offset  Size    Contents
                    0       2       Index to first row below the page break
                    2       2       Index to first column of this page break
                    4       2       Index to last column of this page break

    The row indexes in the lists must be ordered ascending.
    If in BIFF8 a row contains several page breaks, they must be ordered
    ascending by start column index.
    """
    _REC_ID = 0x001B

    def __init__(self, breaks_list):
        self._rec_data = pack('<H', len(breaks_list))
        for r, c1, c2 in breaks_list:
            self._rec_data += pack('<3H', r, c1, c2)

class VerticalPageBreaksRecord(BiffRecord):
    """
    This  record  is  part  of  the  Page  Settings  Block. It contains all
    vertical manual page breaks.

    Record VERTICALPAGEBREAKS, BIFF8:
    Offset  Size  Contents
    0       2     Number of following column index structures (nm)
    2       6nm   List of nm column index structures. Each column index
                  structure contains:
                    Offset  Size    Contents
                    0       2       Index to first column following the page
                                    break
                    2       2       Index to first row of this page break
                    4       2       Index to last row of this page break

    The column indexes in the lists must be ordered ascending.
    If in BIFF8 a column contains several page breaks, they must be ordered
    ascending by start row index.
    """
    _REC_ID = 0x001A

    def __init__(self, breaks_list):
        self._rec_data = pack('<H', len(breaks_list))
        for r, c1, c2 in breaks_list:
            self._rec_data += pack('<3H', r, c1, c2)

class HeaderRecord(BiffRecord):
    """
    This record is part of the Page Settings Block. It specifies the
    page  header  string  for  the current worksheet. If this record is not
    present  or  completely  empty  (record  size is 0), the sheet does not
    contain a page header.

    Record HEADER for non-empty page header, BIFF2-BIFF8:
    Offset      Size    Contents
    0           var.    Page header string
                        BIFF2-BIFF7:    Non-empty byte string, 8bit string
                        length
                        BIFF8: Non-empty Unicode string, 16bit string length
    The  header  string may contain special commands, i.e. placeholders for
    the  page  number,  current  date, or text formatting attributes. These
    fields  are  represented  by  single  letters (exception: font name and
    size,  see  below)  with  a  leading  ampersand ("&"). If the ampersand
    is  part  of the regular header text, it will be duplicated ("&&"). The
    page  header is divided into 3 sections: the left, the centred, and the
    right  section.  Each  section  is introduced by a special command. All
    text  and all commands following are part of the selected section. Each
    section  starts  with the text formatting specified in the default font
    (first  FONT  record  in  the  file). Active formatting attributes from
    a previous section do not go into the next section.

    The following table shows all available commands:

    Command         Contents
    &&              The "&" character itself
    &L              Start of the left section
    &C              Start of the centred section
    &R              Start of the right section
    &P              Current page number
    &N              Page count
    &D              Current date
    &T              Current time
    &A              Sheet name (BIFF5-BIFF8)
    &F              File name without path
    &Z              File path without file name (BIFF8X)
    &G              Picture (BIFF8X)
    &B              Bold on/off (BIFF2-BIFF4)
    &I              Italic on/off (BIFF2-BIFF4)
    &U              Underlining on/off
    &E              Double underlining on/off (BIFF5-BIFF8)
    &S              Strikeout on/off
    &X              Superscript on/off (BIFF5-BIFF8)
    &Y              Subscript on/off (BIFF5-BIFF8)
    &"<fontname>"   Set new font <fontname>
    &"<fontname>,<fontstyle>"
                    Set new font with specified style <fontstyle>.
                    The style <fontstyle> is in most cases one of
                    "Regular", "Bold", "Italic", or "Bold Italic".
                    But this setting is dependent on the used font,
                    it may differ (localised style names, or "Standard",
                    "Oblique", ...). (BIFF5-BIFF8)
    &<fontheight>   Set font height in points (<fontheight> is a decimal value).
                    If this command is followed by a plain number to be printed
                    in the header, it will be separated from the font height
                    with a space character.

    """
    _REC_ID = 0x0014

    def __init__(self, header_str):
        self._rec_data = upack2(header_str)

class FooterRecord(BiffRecord):
    """
    Semantic is equal to HEADER record
    """
    _REC_ID = 0x0015

    def __init__(self, footer_str):
        self._rec_data = upack2(footer_str)


class HCenterRecord(BiffRecord):
    """
    This  record  is  part  of the Page Settings Block. It specifies if the
    sheet is centred horizontally when printed.

    Record HCENTER, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       0 = Print sheet left aligned
                    1 = Print sheet centred horizontally

    """
    _REC_ID = 0x0083

    def __init__(self, is_horz_center):
        self._rec_data = pack('<H', is_horz_center)


class VCenterRecord(BiffRecord):
    """
    This  record  is  part  of the Page Settings Block. It specifies if the
    sheet is centred vertically when printed.

    Record VCENTER, BIFF3-BIFF8:

    Offset  Size    Contents
    0       2       0 = Print sheet aligned at top page border
                    1 = Print sheet vertically centred

    """
    _REC_ID = 0x0084

    def __init__(self, is_vert_center):
        self._rec_data = pack('<H', is_vert_center)


class LeftMarginRecord(BiffRecord):
    """
    This  record  is  part of the Page Settings Block. It contains the left
    page margin of the current worksheet.

    Record LEFTMARGIN, BIFF2-BIFF8:

    Offset  Size    Contents
    0       8       Left page margin in inches
                    (IEEE 754 floating-point value, 64bit double precision)

    """
    _REC_ID = 0x0026

    def __init__(self, margin):
        self._rec_data = pack('<d', margin)


class RightMarginRecord(BiffRecord):
    """
    This  record  is  part of the Page Settings Block. It contains the right
    page margin of the current worksheet.

    Offset  Size    Contents
    0       8       Right page margin in inches
                    (IEEE 754 floating-point value, 64?bit double precision)

    """
    _REC_ID = 0x0027

    def __init__(self, margin):
        self._rec_data = pack('<d', margin)

class TopMarginRecord(BiffRecord):
    """
    This  record  is  part of the Page Settings Block. It contains the top
    page margin of the current worksheet.

    Offset  Size    Contents
    0       8       Top page margin in inches
                    (IEEE 754 floating-point value, 64?bit double precision)

    """
    _REC_ID = 0x0028

    def __init__(self, margin):
        self._rec_data = pack('<d', margin)


class BottomMarginRecord(BiffRecord):
    """
    This  record  is  part of the Page Settings Block. It contains the bottom
    page margin of the current worksheet.

    Offset  Size    Contents
    0       8       Bottom page margin in inches
                    (IEEE 754 floating-point value, 64?bit double precision)

    """
    _REC_ID = 0x0029

    def __init__(self, margin):
        self._rec_data = pack('<d', margin)

class SetupPageRecord(BiffRecord):
    """
    This   record   is  part of the Page Settings Block. It stores the page
    format   settings   of   the  current sheet. The pages may be scaled in
    percent   or  by  using  an  absolute  number of pages. This setting is
    located   in  the  WSBOOL  record.  If  pages  are  scaled in  percent,
    the   scaling  factor  in  this  record is used, otherwise the "Fit  to
    pages"  values. One of the "Fit to pages" values may be 0. In this case
    the sheet is scaled to fit only to the other value.

    Record SETUP, BIFF5-BIFF8:

    Offset      Size    Contents
    0           2       Paper size (see below)
    2           2       Scaling factor in percent
    4           2       Start page number
    6           2       Fit worksheet width to this number of pages
                        (0 = use as many as needed)
    8           2       Fit worksheet height to this number of pages
                        (0 = use as many as needed)
    10          2       Option flags:
                        Bit     Mask        Contents
                        0       0001H       0 = Print pages in columns
                                            1 = Print pages in rows
                        1       0002H       0 = Landscape
                                            1 = Portrait
                        2       0004H       1 = Paper size, scaling factor,
                                            paper orientation (portrait/landscape),
                                            print resolution and number of copies
                                            are not initialised
                        3       0008H       0 = Print coloured
                                            1 = Print black and white
                        4       0010H       0 = Default print quality
                                            1 = Draft quality
                        5       0020H       0 = Do not print cell notes
                                            1 = Print cell notes
                        6       0040H       0 = Paper orientation setting is valid
                                            1 = Paper orientation setting not
                                            initialised
                        7       0080H       0 = Automatic page numbers
                                            1 = Use start page number
                        The following flags are valid for BIFF8 only:
                        9       0200H       0 = Print notes as displayed
                                            1 = Print notes at end of sheet
                        11-10   0C00H       00 = Print errors as displayed
                                            01 = Do not print errors
                                            10 = Print errors as "--"
                                            11 = Print errors as "#N/A!"
    12          2       Print resolution in dpi
    14          2       Vertical print resolution in dpi
    16          8       Header margin (IEEE 754 floating-point value,
                        64bit double precision)
    24          8       Footer margin (IEEE 754 floating-point value,
                        64bit double precision)
    32          2       Number of copies to print


    PAPER TYPES:

    Index   Paper type              Paper size
    0       Undefined
    1       Letter                  8 1/2" x 11"
    2       Letter small            8 1/2" x 11"
    3       Tabloid                 11" x 17"
    4       Ledger                  17" x 11"
    5       Legal                   8 1/2" x 14"
    6       Statement               5 1/2" x 8 1/2"
    7       Executive               7 1/4" x 10 1/2"
    8       A3                      297mm x 420mm
    9       A4                      210mm x 297mm
    10      A4 small                210mm x 297mm
    11      A5                      148mm x 210mm
    12      B4 (JIS)                257mm x 364mm
    13      B5 (JIS)                182mm x 257mm
    14      Folio                   8 1/2" x 13"
    15      Quarto                  215mm x 275mm
    16      10x14                   10" x 14"
    17      11x17                   11" x 17"
    18      Note                    8 1/2" x 11"
    19      Envelope #9             3 7/8" x 8 7/8"
    20      Envelope #10            4 1/8" x 9 1/2"
    21      Envelope #11            4 1/2" x 10 3/8"
    22      Envelope #12            4 3/4" x 11"
    23      Envelope #14            5" x 11 1/2"
    24      C                       17" x 22"
    25      D                       22" x 34"
    26      E                       34" x 44"
    27      Envelope DL             110mm x 220mm
    28      Envelope C5             162mm x 229mm
    29      Envelope C3             324mm x 458mm
    30      Envelope C4             229mm x 324mm
    31      Envelope C6             114mm x 162mm
    32      Envelope C6/C5          114mm x 229mm
    33      B4 (ISO)                250mm x 353mm
    34      B5 (ISO)                176mm x 250mm
    35      B6 (ISO)                125mm x 176mm
    36      Envelope Italy          110mm x 230mm
    37      Envelope Monarch        3 7/8" x 7 1/2"
    38      63/4 Envelope           3 5/8" x 6 1/2"
    39      US Standard Fanfold     14 7/8" x 11"
    40      German Std. Fanfold     8 1/2" x 12"
    41      German Legal Fanfold    8 1/2" x 13"
    42      B4 (ISO)                250mm x 353mm
    43      Japanese Postcard       100mm x 148mm
    44      9x11                    9" x 11"
    45      10x11                   10" x 11"
    46      15x11                   15" x 11"
    47      Envelope Invite         220mm x 220mm
    48      Undefined
    49      Undefined
    50      Letter Extra            9 1/2" x 12"
    51      Legal Extra             9 1/2" x 15"
    52      Tabloid Extra           11 11/16" x 18"
    53      A4 Extra                235mm x 322mm
    54      Letter Transverse       8 1/2" x 11"
    55      A4 Transverse           210mm x 297mm
    56      Letter Extra Transv.    9 1/2" x 12"
    57      Super A/A4              227mm x 356mm
    58      Super B/A3              305mm x 487mm
    59      Letter Plus             8 1/2" x 12 11/16"
    60      A4 Plus                 210mm x 330mm
    61      A5 Transverse           148mm x 210mm
    62      B5 (JIS) Transverse     182mm x 257mm
    63      A3 Extra                322mm x 445mm
    64      A5 Extra                174mm x 235mm
    65      B5 (ISO) Extra          201mm x 276mm
    66      A2                      420mm x 594mm
    67      A3 Transverse           297mm x 420mm
    68      A3 Extra Transverse     322mm x 445mm
    69      Dbl. Japanese Postcard  200mm x 148mm
    70      A6                      105mm x 148mm
    71
    72
    73
    74
    75      Letter Rotated          11" x 8 1/2"
    76      A3 Rotated              420mm x 297mm
    77      A4 Rotated              297mm x 210mm
    78      A5 Rotated              210mm x 148mm
    79      B4 (JIS) Rotated        364mm x 257mm
    80      B5 (JIS) Rotated        257mm x 182mm
    81      Japanese Postcard Rot.  148mm x 100mm
    82      Dbl. Jap. Postcard Rot. 148mm x 200mm
    83      A6 Rotated              148mm x 105mm
    84
    85
    86
    87
    88      B6 (JIS)                128mm x 182mm
    89      B6 (JIS) Rotated        182mm x 128mm
    90      12x11                   12" x 11"

    """
    _REC_ID = 0x00A1
    def __init__(self, paper, scaling, start_num, fit_width_to, fit_height_to,
                    options,
                    hres, vres,
                    header_margin, footer_margin,
                    num_copies):
        self._rec_data = pack('<8H2dH', paper, scaling, start_num,
                                        fit_width_to, fit_height_to, \
                                        options,
                                        hres, vres,
                                        header_margin, footer_margin,
                                        num_copies)

class NameRecord(BiffRecord):
    """
    This record is part of a Link Table. It contains the name and the token
    array of an internal defined name. Token arrays of defined names
    contain tokens with aberrant token classes.

    Record NAME, BIFF5/BIFF7:
    Offset      Size    Contents
       0          2     Option flags, see below
       2          1     Keyboard shortcut (only for command macro names, see below)
       3          1     Length of the name (character count, ln)
       4          2     Size of the formula data (sz)
       6          2     0 = Global name, otherwise index to EXTERNSHEET record (one-based)
       8          2     0 = Global name, otherwise index to sheet (one-based)
      10          1     Length of menu text (character count, lm)
      11          1     Length of description text (character count, ld)
      12          1     Length of help topic text (character count, lh)
      13          1     Length of status bar text (character count, ls)
      14         ln     Character array of the name
    14+ln        sz     Formula data (RPN token array without size field, 4)
  14+ln+sz       lm     Character array of menu text
     var.        ld     Character array of description text
     var.        lh     Character array of help topic text
     var.        ls     Character array of status bar text

    Record NAME, BIFF8:
    Offset      Size Contents
       0          2  Option flags, see below
       2          1  Keyboard shortcut (only for command macro names, see below)
       3          1  Length of the name (character count, ln)
       4          2  Size of the formula data (sz)
       6          2  Not used
       8          2  0 = Global name, otherwise index to sheet (one-based)
      10          1  Length of menu text (character count, lm)
      11          1  Length of description text (character count, ld)
      12          1  Length of help topic text (character count, lh)
      13          1  Length of status bar text (character count, ls)
      14        var. Name (Unicode string without length field, 3.4)
     var.        sz  Formula data (RPN token array without size field, 4)
    [var.]      var. (optional, only if lm > 0) Menu text (Unicode string without length field, 3.4)
    [var.]      var. (optional, only if ld > 0) Description text (Unicode string without length field, 3.4)
    [var.]      var. (optional, only if lh > 0) Help topic text (Unicode string without length field, 3.4)
    [var.]      var. (optional, only if ls > 0) Status bar text (Unicode string without length field, 3.4)
    """
    _REC_ID = 0x0018

    def __init__(self, options, keyboard_shortcut, name, sheet_index, rpn, menu_text='', desc_text='', help_text='', status_text=''):
        if type(name) == int:
            uname = chr(name)
        else:
            uname = upack1(name)[1:]
        uname_len = len(uname)

        #~ self._rec_data = pack('<HBBHHHBBBB%ds%ds' % (uname_len, len(rpn)), options, keyboard_shortcut, uname_len, len(rpn), 0x0000, sheet_index, len(menu_text), len(desc_text), len(help_text), len(status_text), uname, rpn) + menu_text + desc_text + help_text + status_text
        self._rec_data = pack('<HBBHHHBBBBB%ds%ds' % (uname_len, len(rpn)), options, keyboard_shortcut, uname_len, len(rpn), 0x0000, sheet_index, 0x00, len(menu_text), len(desc_text), len(help_text), len(status_text), uname, rpn) + menu_text + desc_text + help_text + status_text

# Excel (both 2003 and 2007) don't like refs
# split over a record boundary, which is what the
# standard BiffRecord.get method does.

# 8224 max data bytes in a BIFF record
# 6 bytes per ref
# 1370 = floor((8224 - 2) / 6.0) max refs in a record

_maxRefPerRecord = 1370

class ExternSheetRecord(BiffRecord):
    """
    In BIFF8 the record stores a list with indexes to SUPBOOK
    records (list of REF structures, 6.100). See 5.10.3 for
    details about external references in BIFF8.

    Record EXTERNSHEET, BIFF8:
    Offset          Size      Contents
       0             2        Number of following REF structures (nm)
       2           6nm        List of nm REF structures. Each REF contains the following data:
                              Offset     Size     Contents
                                 0         2      Index to SUPBOOK record
                                 2         2      Index to first SUPBOOK sheet
                                 4         2      Index to last SUPBOOK sheet
    """
    _REC_ID = 0x0017

    def __init__(self, refs):

        # do we always need this ref? or only if there are no refs?
        # (I believe that if there are no refs then we should not generate the link table - Ruben)
        #refs.insert(0, (0,0,0))

        self.refs = refs

    def get(self):
        res = []
        nrefs = len(self.refs)
        for idx in xrange(0, nrefs, _maxRefPerRecord):
            chunk = self.refs[idx:idx+_maxRefPerRecord]
            krefs = len(chunk)
            if idx: # CONTINUE record
                header = pack("<HH", 0x003C, 6 * krefs)
            else: # ExternSheetRecord
                header = pack("<HHH", self._REC_ID, 6 * krefs + 2, nrefs)
            res.append(header)
            res.extend(pack("<HHH", *r) for r in chunk)
        return b''.join(res)

class SupBookRecord(BiffRecord):
    """
    This record mainly stores the URL of an external document
    and a list of sheet names inside this document. Furthermore
    it is used to store DDE and OLE object links, or to indicate
    an internal 3D reference or an add-in function. See 5.10.3
    for details about external references in BIFF8.

    """
    _REC_ID = 0x01AE

class InternalReferenceSupBookRecord(SupBookRecord):
    """
    In each file occurs a SUPBOOK that is used for internal 3D
    references. It stores the number of sheets of the own document.

    Record SUPBOOK for 3D references, BIFF8:
    Offset         Size   Contents
      0             2     Number of sheets in this document
      2             2     01H 04H (relict of BIFF5/BIFF7, the byte string "<04H>", see 3.9.1)

    """

    def __init__(self, num_sheets):
        self._rec_data = pack('<HBB', num_sheets, 0x01, 0x04)

class XcallSupBookRecord(SupBookRecord):
    """
    Add-in function names are stored in EXTERNNAME records following this record.

    Offset  Size    Contents
    0       2       0001H
    2       2       01H 3AH (relict of BIFF5, the byte string ':', see EXTERNSHEET record, 5.41)

    """

    def __init__(self):
        self._rec_data = pack('<HBB', 1, 0x01, 0x3A)


class ExternnameRecord(BiffRecord):
    """
    Record EXTERNNAME for external names and Analysis add-in functions, BIFF5-BIFF8:
    Offset  Size    Contents
    0       2       Option flags (see below)
    2       2       0 for global names, or:
                    BIFF5: One-based index to EXTERNSHEET record containing the sheet name,
                    BIFF8: One-based index to sheet list in preceding EXTERNALBOOK record.
    4       2       Not used
    6       var.    BIFF5: Name (byte string, 8-bit string length, ?2.5.2).
                    BIFF8: Name (Unicode string, 8-bit string length, ?2.5.3).
                    See DEFINEDNAME record (?5.33) for a list of built-in names, if the built-in flag is set
                    in the option flags above.
    var.    var.    Formula data (RPN token array, ?3)

    Option flags for external names (BIFF5-BIFF8)
    Bit     Mask    Contents
    0       0001H   0 = Standard name; 1 = Built-in name
    1       0002H   0 = Manual link; 1 = Automatic link (DDE links and OLE links only)
    2       0004H   1 = Picture link (DDE links and OLE links only)
    3       0008H   1 = This is the “StdDocumentName” identifier (DDE links only)
    4       0010H   1 = OLE link
    14-5    7FE0H   Clipboard format of last successful update (DDE links and OLE links only)
    15      8000H   1 = Iconified picture link (BIFF8 OLE links only)
    """
    _REC_ID = 0x0023

    def __init__(self, options=0, index=0, name=None, fmla=None):
        self._rec_data = pack('<HHH', options, index, 0) + upack1(name) + fmla

