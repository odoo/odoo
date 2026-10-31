##
# Portions copyright (c) 2008-2012 Stephen John Machin, Lingfo Pty Ltd
# This module is part of the xlrd package, which is released under a BSD-style licence.
##

from __future__ import print_function, unicode_literals

import re
import sys
from os.path import join, normpath

from .biffh import (
    XL_CELL_BLANK, XL_CELL_BOOLEAN, XL_CELL_ERROR, XL_CELL_TEXT, XLRDError,
    error_text_from_code,
)
from .book import Book, Name
from .formatting import XF, Format, is_date_format_string
from .sheet import Sheet
from .timemachine import *

DEBUG = 0


DLF = sys.stdout # Default Log File

ET = None
ET_has_iterparse = False
Element_has_iter = False

def ensure_elementtree_imported(verbosity, logfile):
    global ET, ET_has_iterparse, Element_has_iter
    if ET is not None:
        return
    if "IronPython" in sys.version:
        import xml.etree.ElementTree as ET
        #### 2.7.2.1: fails later with
        #### NotImplementedError: iterparse is not supported on IronPython. (CP #31923)
    else:
        try: import defusedxml.cElementTree as ET
        except ImportError:
            try: import xml.etree.cElementTree as ET
            except ImportError:
                try: import cElementTree as ET
                except ImportError:
                    try: import lxml.etree as ET
                    except ImportError:
                        try: import xml.etree.ElementTree as ET
                        except ImportError:
                            try: import elementtree.ElementTree as ET
                            except ImportError:
                                raise Exception("Failed to import an ElementTree implementation")
    if hasattr(ET, 'iterparse'):
        _dummy_stream = BYTES_IO(b'')
        try:
            ET.iterparse(_dummy_stream)
            ET_has_iterparse = True
        except NotImplementedError:
            pass
    Element_has_iter = hasattr(ET, 'ElementTree') and hasattr(ET.ElementTree, 'iter')
    if verbosity:
        etree_version = repr([
            (item, getattr(ET, item))
            for item in ET.__dict__.keys()
            if item.lower().replace('_', '') == 'version'
        ])
        print(ET.__file__, ET.__name__, etree_version, ET_has_iterparse, file=logfile)

def split_tag(tag):
    pos = tag.rfind('}') + 1
    if pos >= 2:
        return tag[:pos], tag[pos:]
    return '', tag

def augment_keys(adict, uri):
    # uri must already be enclosed in {}
    for x in list(adict.keys()):
        adict[uri + x] = adict[x]

_UPPERCASE_1_REL_INDEX = {} # Used in fast conversion of column names (e.g. "XFD") to indices (16383)
for _x in xrange(26):
    _UPPERCASE_1_REL_INDEX["ABCDEFGHIJKLMNOPQRSTUVWXYZ"[_x]] = _x + 1
for _x in "123456789":
    _UPPERCASE_1_REL_INDEX[_x] = 0
del _x

def cell_name_to_rowx_colx(cell_name, letter_value=_UPPERCASE_1_REL_INDEX,
        allow_no_col=False):
    # Extract column index from cell name
    # A<row number> => 0, Z =>25, AA => 26, XFD => 16383
    colx = 0
    charx = -1
    try:
        for c in cell_name:
            charx += 1
            lv = letter_value[c]
            if lv:
                colx = colx * 26 + lv
            else: # start of row number; can't be '0'
                if charx == 0:
                    # there was no col marker
                    if allow_no_col:
                        colx = None
                        break
                    else:
                        raise Exception(
                                'Missing col in cell name %r', cell_name)
                else:
                    colx = colx - 1
                    assert 0 <= colx < X12_MAX_COLS
                    break
    except KeyError:
        raise Exception('Unexpected character %r in cell name %r' % (c, cell_name))
    rowx = int(cell_name[charx:]) - 1
    return rowx, colx

error_code_from_text = {}
for _code, _text in error_text_from_code.items():
    error_code_from_text[_text] = _code

# === X12 === Excel 2007 .xlsx ===============================================

U_SSML12 = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
U_ODREL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
U_PKGREL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
U_CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
U_DC = "{http://purl.org/dc/elements/1.1/}"
U_DCTERMS = "{http://purl.org/dc/terms/}"
XML_SPACE_ATTR = "{http://www.w3.org/XML/1998/namespace}space"
XML_WHITESPACE = "\t\n \r"
X12_MAX_ROWS = 2 ** 20
X12_MAX_COLS = 2 ** 14
V_TAG = U_SSML12 + 'v' # cell child: value
F_TAG = U_SSML12 + 'f' # cell child: formula
IS_TAG = U_SSML12 + 'is' # cell child: inline string

def unescape(s,
             subber=re.compile(r'_x[0-9A-Fa-f]{4,4}_', re.UNICODE).sub,
             repl=lambda mobj: unichr(int(mobj.group(0)[2:6], 16))):
    if "_" in s:
        return subber(repl, s)
    return s

def cooked_text(self, elem):
    t = elem.text
    if t is None:
        return ''
    if elem.get(XML_SPACE_ATTR) != 'preserve':
        t = t.strip(XML_WHITESPACE)
    return ensure_unicode(unescape(t))

def get_text_from_si_or_is(self, elem, r_tag=U_SSML12+'r', t_tag=U_SSML12 +'t'):
    "Returns unescaped unicode"
    accum = []
    for child in elem:
        # self.dump_elem(child)
        tag = child.tag
        if tag == t_tag:
            t = cooked_text(self, child)
            if t: # note: .text attribute can be None
                accum.append(t)
        elif tag == r_tag:
            for tnode in child:
                if tnode.tag == t_tag:
                    t = cooked_text(self, tnode)
                    if t:
                        accum.append(t)
    return ''.join(accum)

def map_attributes(amap, elem, obj):
    for xml_attr, obj_attr, cnv_func_or_const in amap:
        if not xml_attr:
            setattr(obj, obj_attr, cnv_func_or_const)
            continue
        if not obj_attr: continue #### FIX ME ####
        raw_value = elem.get(xml_attr)
        cooked_value = cnv_func_or_const(raw_value)
        setattr(obj, obj_attr, cooked_value)

def cnv_ST_Xstring(s):
    if s is None: return ""
    return ensure_unicode(s)

def cnv_xsd_unsignedInt(s):
    if not s:
        return None
    value = int(s)
    assert value >= 0
    return value

def cnv_xsd_boolean(s):
    if not s:
        return 0
    if s in ("1", "true", "on"):
        return 1
    if s in ("0", "false", "off"):
        return 0
    raise ValueError("unexpected xsd:boolean value: %r" % s)


_defined_name_attribute_map = (
    ("name",                "name",         cnv_ST_Xstring, ),
    ("comment",             "",             cnv_ST_Xstring, ),
    ("customMenu",          "",             cnv_ST_Xstring, ),
    ("description",         "",             cnv_ST_Xstring, ),
    ("help",                "",             cnv_ST_Xstring, ),
    ("statusBar",           "",             cnv_ST_Xstring, ),
    ("localSheetId",        "scope",        cnv_xsd_unsignedInt, ),
    ("hidden",              "hidden",       cnv_xsd_boolean, ),
    ("function",            "func",         cnv_xsd_boolean, ),
    ("vbProcedure",         "vbasic",       cnv_xsd_boolean, ),
    ("xlm",                 "macro",        cnv_xsd_boolean, ),
    ("functionGroupId",     "funcgroup",    cnv_xsd_unsignedInt, ),
    ("shortcutKey",         "",             cnv_ST_Xstring,  ),
    ("publishToServer",     "",             cnv_xsd_boolean, ),
    ("workbookParameter",   "",             cnv_xsd_boolean, ),
    ("",                    "any_err",      0,               ),
    ("",                    "any_external", 0,               ),
    ("",                    "any_rel",      0,               ),
    ("",                    "basic_formula_len", 0,          ),
    ("",                    "binary",       0,               ),
    ("",                    "builtin",      0,               ),
    ("",                    "complex",      0,               ),
    ("",                    "evaluated",    0,               ),
    ("",                    "excel_sheet_index", 0,          ),
    ("",                    "excel_sheet_num", 0,            ),
    ("",                    "option_flags", 0,               ),
    ("",                    "result",       None,            ),
    ("",                    "stack",        None,            ),
)

def make_name_access_maps(bk):
    name_and_scope_map = {} # (name.lower(), scope): Name_object
    name_map = {}           # name.lower() : list of Name_objects (sorted in scope order)
    num_names = len(bk.name_obj_list)
    for namex in xrange(num_names):
        nobj = bk.name_obj_list[namex]
        name_lcase = nobj.name.lower()
        key = (name_lcase, nobj.scope)
        if key in name_and_scope_map:
            msg = 'Duplicate entry %r in name_and_scope_map' % (key, )
            if 0:
                raise XLRDError(msg)
            else:
                if bk.verbosity:
                    print(msg, file=bk.logfile)
        name_and_scope_map[key] = nobj
        sort_data = (nobj.scope, namex, nobj)
        if name_lcase in name_map:
            name_map[name_lcase].append(sort_data)
        else:
            name_map[name_lcase] = [sort_data]
    for key in name_map.keys():
        alist = name_map[key]
        alist.sort()
        name_map[key] = [x[2] for x in alist]
    bk.name_and_scope_map = name_and_scope_map
    bk.name_map = name_map

class X12General(object):

    def process_stream(self, stream, heading=None):
        if self.verbosity >= 2 and heading is not None:
            fprintf(self.logfile, "\n=== %s ===\n", heading)
        self.tree = ET.parse(stream)
        getmethod = self.tag2meth.get
        for elem in self.tree.iter() if Element_has_iter else self.tree.getiterator():
            if self.verbosity >= 3:
                self.dump_elem(elem)
            meth = getmethod(elem.tag)
            if meth:
                meth(self, elem)
        self.finish_off()

    def finish_off(self):
        pass

    def dump_elem(self, elem):
        fprintf(self.logfile,
            "===\ntag=%r len=%d attrib=%r text=%r tail=%r\n",
            split_tag(elem.tag)[1], len(elem), elem.attrib, elem.text, elem.tail)

    def dumpout(self, fmt, *vargs):
        text = (12 * ' ' + fmt + '\n') % vargs
        self.logfile.write(text)

class X12Book(X12General):

    def __init__(self, bk, logfile=DLF, verbosity=False):
        self.bk = bk
        self.logfile = logfile
        self.verbosity = verbosity
        self.bk.nsheets = 0
        self.bk.props = {}
        self.relid2path = {}
        self.relid2reltype = {}
        self.sheet_targets = [] # indexed by sheetx
        self.sheetIds = [] # indexed by sheetx

    core_props_menu = {
        U_CP+"lastModifiedBy": ("last_modified_by", cnv_ST_Xstring),
        U_DC+"creator": ("creator", cnv_ST_Xstring),
        U_DCTERMS+"modified": ("modified", cnv_ST_Xstring),
        U_DCTERMS+"created": ("created", cnv_ST_Xstring),
    }

    def process_coreprops(self, stream):
        if self.verbosity >= 2:
            fprintf(self.logfile, "\n=== coreProps ===\n")
        self.tree = ET.parse(stream)
        getmenu = self.core_props_menu.get
        props = {}
        for elem in self.tree.iter() if Element_has_iter else self.tree.getiterator():
            if self.verbosity >= 3:
                self.dump_elem(elem)
            menu = getmenu(elem.tag)
            if menu:
                attr, func = menu
                value = func(elem.text)
                props[attr] = value
        self.bk.user_name = props.get('last_modified_by') or props.get('creator')
        self.bk.props = props
        if self.verbosity >= 2:
            fprintf(self.logfile, "props: %r\n", props)
        self.finish_off()

    @staticmethod
    def convert_filename(name):
        return name.replace('\\', '/').lower()

    def process_rels(self, stream):
        if self.verbosity >= 2:
            fprintf(self.logfile, "\n=== Relationships ===\n")
        tree = ET.parse(stream)
        r_tag = U_PKGREL + 'Relationship'
        for elem in tree.findall(r_tag):
            rid = elem.get('Id')
            target = X12Book.convert_filename(elem.get('Target'))
            reltype = elem.get('Type').split('/')[-1]
            if self.verbosity >= 2:
                self.dumpout('Id=%r Type=%r Target=%r', rid, reltype, target)
            self.relid2reltype[rid] = reltype
            # self.relid2path[rid] = 'xl/' + target
            if target.startswith('/'):
                self.relid2path[rid]  = target[1:] # drop the /
            else:
                self.relid2path[rid] = 'xl/' + target

    def do_defined_name(self, elem):
        #### UNDER CONSTRUCTION ####
        if 0 and self.verbosity >= 3:
            self.dump_elem(elem)
        nobj = Name()
        bk = self.bk
        nobj.bk = bk
        nobj.name_index = len(bk.name_obj_list)
        bk.name_obj_list.append(nobj)
        nobj.name = elem.get('name')
        nobj.raw_formula = None # compiled bytecode formula -- not in XLSX
        nobj.formula_text = cooked_text(self, elem)
        map_attributes(_defined_name_attribute_map, elem, nobj)
        if nobj.scope is None:
            nobj.scope = -1 # global
        if nobj.name.startswith("_xlnm."):
            nobj.builtin = 1
        if self.verbosity >= 2:
            nobj.dump(header='=== Name object ===')

    def do_defined_names(self, elem):
        for child in elem:
            self.do_defined_name(child)
        make_name_access_maps(self.bk)

    def do_sheet(self, elem):
        bk = self.bk
        sheetx = bk.nsheets
        # print elem.attrib
        rid = elem.get(U_ODREL + 'id')
        sheetId = int(elem.get('sheetId'))
        name = unescape(ensure_unicode(elem.get('name')))
        reltype = self.relid2reltype[rid]
        target = self.relid2path[rid]
        if self.verbosity >= 2:
            self.dumpout(
                'sheetx=%d sheetId=%r rid=%r type=%r name=%r',
                sheetx, sheetId, rid, reltype, name)
        if reltype != 'worksheet':
            if self.verbosity >= 2:
                self.dumpout('Ignoring sheet of type %r (name=%r)', reltype, name)
            return
        state = elem.get('state')
        visibility_map = {
            None: 0,
            'visible': 0,
            'hidden': 1,
            'veryHidden': 2,
        }
        bk._sheet_visibility.append(visibility_map[state])
        sheet = Sheet(bk, position=None, name=name, number=sheetx)
        sheet.utter_max_rows = X12_MAX_ROWS
        sheet.utter_max_cols = X12_MAX_COLS
        bk._sheet_list.append(sheet)
        bk._sheet_names.append(name)
        bk.nsheets += 1
        self.sheet_targets.append(target)
        self.sheetIds.append(sheetId)


    def do_workbookpr(self, elem):
        datemode = cnv_xsd_boolean(elem.get('date1904'))
        if self.verbosity >= 2:
            self.dumpout('datemode=%r', datemode)
        self.bk.datemode = datemode

    tag2meth = {
        'definedNames':  do_defined_names,
        'workbookPr':   do_workbookpr,
        'sheet':        do_sheet,
    }
    augment_keys(tag2meth, U_SSML12)

class X12SST(X12General):

    def __init__(self, bk, logfile=DLF, verbosity=0):
        self.bk = bk
        self.logfile = logfile
        self.verbosity = verbosity
        if ET_has_iterparse:
            self.process_stream = self.process_stream_iterparse
        else:
            self.process_stream = self.process_stream_findall

    def process_stream_iterparse(self, stream, heading=None):
        if self.verbosity >= 2 and heading is not None:
            fprintf(self.logfile, "\n=== %s ===\n", heading)
        si_tag = U_SSML12 + 'si'
        elemno = -1
        sst = self.bk._sharedstrings
        for event, elem in ET.iterparse(stream):
            if elem.tag != si_tag: continue
            elemno = elemno + 1
            if self.verbosity >= 3:
                fprintf(self.logfile, "element #%d\n", elemno)
                self.dump_elem(elem)
            result = get_text_from_si_or_is(self, elem)
            sst.append(result)
            elem.clear() # destroy all child elements
        if self.verbosity >= 2:
            self.dumpout('Entries in SST: %d', len(sst))
        if self.verbosity >= 3:
            for x, s in enumerate(sst):
                fprintf(self.logfile, "SST x=%d s=%r\n", x, s)

    def process_stream_findall(self, stream, heading=None):
        if self.verbosity >= 2 and heading is not None:
            fprintf(self.logfile, "\n=== %s ===\n", heading)
        self.tree = ET.parse(stream)
        si_tag = U_SSML12 + 'si'
        elemno = -1
        sst = self.bk._sharedstrings
        for elem in self.tree.findall(si_tag):
            elemno = elemno + 1
            if self.verbosity >= 3:
                fprintf(self.logfile, "element #%d\n", elemno)
                self.dump_elem(elem)
            result = get_text_from_si_or_is(self, elem)
            sst.append(result)
        if self.verbosity >= 2:
            self.dumpout('Entries in SST: %d', len(sst))

class X12Styles(X12General):

    def __init__(self, bk, logfile=DLF, verbosity=0):
        self.bk = bk
        self.logfile = logfile
        self.verbosity = verbosity
        self.xf_counts = [0, 0]
        self.xf_type = None
        self.fmt_is_date = {}
        for x in list(range(14, 23)) + list(range(45, 48)): #### hard-coding FIX ME ####
            self.fmt_is_date[x] = 1
        # dummy entry for XF 0 in case no Styles section
        self.bk._xf_index_to_xl_type_map[0] = 2
        # fill_in_standard_formats(bk) #### pre-integration kludge

    def do_cellstylexfs(self, elem):
        self.xf_type = 0

    def do_cellxfs(self, elem):
        self.xf_type = 1

    def do_numfmt(self, elem):
        formatCode = ensure_unicode(elem.get('formatCode'))
        numFmtId = int(elem.get('numFmtId'))
        is_date = is_date_format_string(self.bk, formatCode)
        self.fmt_is_date[numFmtId] = is_date
        fmt_obj = Format(numFmtId, is_date + 2, formatCode)
        self.bk.format_map[numFmtId] = fmt_obj
        if self.verbosity >= 3:
            self.dumpout('numFmtId=%d formatCode=%r is_date=%d', numFmtId, formatCode, is_date)

    def do_xf(self, elem):
        if self.xf_type != 1:
            #### ignoring style XFs for the moment
            return
        xfx = self.xf_counts[self.xf_type]
        self.xf_counts[self.xf_type] = xfx + 1
        xf = XF()
        self.bk.xf_list.append(xf)
        self.bk.xfcount += 1
        numFmtId = int(elem.get('numFmtId', '0'))
        xf.format_key = numFmtId
        is_date = self.fmt_is_date.get(numFmtId, 0)
        self.bk._xf_index_to_xl_type_map[xfx] = is_date + 2
        if self.verbosity >= 3:
            self.dumpout('xfx=%d numFmtId=%d', xfx, numFmtId)
            self.dumpout(repr(self.bk._xf_index_to_xl_type_map))

    tag2meth = {
        'cellStyleXfs': do_cellstylexfs,
        'cellXfs':      do_cellxfs,
        'numFmt':       do_numfmt,
        'xf':           do_xf,
    }
    augment_keys(tag2meth, U_SSML12)

class X12Sheet(X12General):

    def __init__(self, sheet, logfile=DLF, verbosity=0):
        self.sheet = sheet
        self.logfile = logfile
        self.verbosity = verbosity
        self.rowx = -1 # We may need to count them.
        self.bk = sheet.book
        self.sst = self.bk._sharedstrings
        self.relid2path = {}
        self.relid2reltype = {}
        self.merged_cells = sheet.merged_cells
        self.warned_no_cell_name = 0
        self.warned_no_row_num = 0
        if ET_has_iterparse:
            self.process_stream = self.own_process_stream

    def own_process_stream(self, stream, heading=None):
        if self.verbosity >= 2 and heading is not None:
            fprintf(self.logfile, "\n=== %s ===\n", heading)
        row_tag = U_SSML12 + "row"
        self_do_row = self.do_row
        for event, elem in ET.iterparse(stream):
            if elem.tag == row_tag:
                self_do_row(elem)
                elem.clear() # destroy all child elements (cells)
            elif elem.tag == U_SSML12 + "dimension":
                self.do_dimension(elem)
            elif elem.tag == U_SSML12 + "mergeCell":
                self.do_merge_cell(elem)
        self.finish_off()

    def process_rels(self, stream):
        if self.verbosity >= 2:
            fprintf(self.logfile, "\n=== Sheet Relationships ===\n")
        tree = ET.parse(stream)
        r_tag = U_PKGREL + 'Relationship'
        for elem in tree.findall(r_tag):
            rid = elem.get('Id')
            target = elem.get('Target')
            reltype = elem.get('Type').split('/')[-1]
            if self.verbosity >= 2:
                self.dumpout('Id=%r Type=%r Target=%r', rid, reltype, target)
            self.relid2reltype[rid] = reltype
            self.relid2path[rid] = normpath(join('xl/worksheets', target))

    def process_comments_stream(self, stream):
        root = ET.parse(stream).getroot()
        author_list = root[0]
        assert author_list.tag == U_SSML12 + 'authors'
        authors = [elem.text for elem in author_list]
        comment_list = root[1]
        assert comment_list.tag == U_SSML12 + 'commentList'
        cell_note_map = self.sheet.cell_note_map
        from .sheet import Note
        text_tag = U_SSML12 + 'text'
        r_tag = U_SSML12 + 'r'
        t_tag = U_SSML12 + 't'
        for elem in comment_list.findall(U_SSML12 + 'comment'):
            ts = elem.findall('./' + text_tag + '/' + t_tag)
            ts += elem.findall('./' + text_tag + '/' + r_tag + '/' + t_tag)
            ref = elem.get('ref')
            note = Note()
            note.author = authors[int(elem.get('authorId'))]
            note.rowx, note.colx = coords = cell_name_to_rowx_colx(ref)
            note.text = ''
            for t in ts:
                note.text += cooked_text(self, t)
            cell_note_map[coords] = note

    def do_dimension(self, elem):
        ref = elem.get('ref') # example: "A1:Z99" or just "A1"
        if ref:
            # print >> self.logfile, "dimension: ref=%r" % ref
            last_cell_ref = ref.split(':')[-1] # example: "Z99"
            rowx, colx = cell_name_to_rowx_colx(
                    last_cell_ref, allow_no_col=True)
            self.sheet._dimnrows = rowx + 1
            if colx is not None:
                self.sheet._dimncols = colx + 1

    def do_merge_cell(self, elem):
        # The ref attribute should be a cell range like "B1:D5".
        ref = elem.get('ref')
        if ref:
            try:
                first_cell_ref, last_cell_ref = ref.split(':')
            except ValueError:
                # encountered a single cell merge, e.g. "B3"
                first_cell_ref = ref
                last_cell_ref = ref
            first_rowx, first_colx = cell_name_to_rowx_colx(first_cell_ref)
            last_rowx, last_colx = cell_name_to_rowx_colx(last_cell_ref)
            self.merged_cells.append((first_rowx, last_rowx + 1,
                                      first_colx, last_colx + 1))

    def do_row(self, row_elem):

        def bad_child_tag(child_tag):
            raise Exception('cell type %s has unexpected child <%s> at rowx=%r colx=%r' % (cell_type, child_tag, rowx, colx))

        row_number = row_elem.get('r')
        if row_number is None: # Yes, it's optional.
            self.rowx += 1
            explicit_row_number = 0
            if self.verbosity and not self.warned_no_row_num:
                self.dumpout("no row number; assuming rowx=%d", self.rowx)
                self.warned_no_row_num = 1
        else:
            self.rowx = int(row_number) - 1
            explicit_row_number = 1
        assert 0 <= self.rowx < X12_MAX_ROWS
        rowx = self.rowx
        colx = -1
        if self.verbosity >= 3:
            self.dumpout("<row> row_number=%r rowx=%d explicit=%d",
                row_number, self.rowx, explicit_row_number)
        letter_value = _UPPERCASE_1_REL_INDEX
        for cell_elem in row_elem:
            cell_name = cell_elem.get('r')
            if cell_name is None: # Yes, it's optional.
                colx += 1
                if self.verbosity and not self.warned_no_cell_name:
                    self.dumpout("no cellname; assuming rowx=%d colx=%d", rowx, colx)
                    self.warned_no_cell_name = 1
            else:
                # Extract column index from cell name
                # A<row number> => 0, Z =>25, AA => 26, XFD => 16383
                colx = 0
                charx = -1
                try:
                    for c in cell_name:
                        charx += 1
                        if c == '$':
                            continue
                        lv = letter_value[c]
                        if lv:
                            colx = colx * 26 + lv
                        else: # start of row number; can't be '0'
                            colx = colx - 1
                            assert 0 <= colx < X12_MAX_COLS
                            break
                except KeyError:
                    raise Exception('Unexpected character %r in cell name %r' % (c, cell_name))
                if explicit_row_number and cell_name[charx:] != row_number:
                    raise Exception('cell name %r but row number is %r' % (cell_name, row_number))
            xf_index = int(cell_elem.get('s', '0'))
            cell_type = cell_elem.get('t', 'n')
            tvalue = None
            if cell_type == 'n':
                # n = number. Most frequent type.
                # <v> child contains plain text which can go straight into float()
                # OR there's no text in which case it's a BLANK cell
                for child in cell_elem:
                    child_tag = child.tag
                    if child_tag == V_TAG:
                        tvalue = child.text
                    elif child_tag == F_TAG:
                        # formula
                        pass
                    else:
                        raise Exception('unexpected tag %r' % child_tag)
                if not tvalue:
                    if self.bk.formatting_info:
                        self.sheet.put_cell(rowx, colx, XL_CELL_BLANK, '', xf_index)
                else:
                    self.sheet.put_cell(rowx, colx, None, float(tvalue), xf_index)
            elif cell_type == "s":
                # s = index into shared string table. 2nd most frequent type
                # <v> child contains plain text which can go straight into int()
                for child in cell_elem:
                    child_tag = child.tag
                    if child_tag == V_TAG:
                        tvalue = child.text
                    elif child_tag == F_TAG:
                        # formula not expected here, but gnumeric does it.
                        pass
                    else:
                        bad_child_tag(child_tag)
                if not tvalue:
                    # <c r="A1" t="s"/>
                    if self.bk.formatting_info:
                        self.sheet.put_cell(rowx, colx, XL_CELL_BLANK, '', xf_index)
                else:
                    value = self.sst[int(tvalue)]
                    self.sheet.put_cell(rowx, colx, XL_CELL_TEXT, value, xf_index)
            elif cell_type == "str":
                # str = string result from formula.
                # Should have <f> (formula) child; however in one file, all text cells are str with no formula.
                # <v> child can contain escapes
                for child in cell_elem:
                    child_tag = child.tag
                    if child_tag == V_TAG:
                        tvalue = cooked_text(self, child)
                    elif child_tag == F_TAG:
                        # formula
                        pass
                    else:
                        bad_child_tag(child_tag)
                # assert tvalue is not None and formula is not None
                # Yuk. Fails with file created by gnumeric -- no tvalue!
                self.sheet.put_cell(rowx, colx, XL_CELL_TEXT, tvalue, xf_index)
            elif cell_type == "b":
                # b = boolean
                # <v> child contains "0" or "1"
                for child in cell_elem:
                    child_tag = child.tag
                    if child_tag == V_TAG:
                        tvalue = child.text
                    elif child_tag == F_TAG:
                        # formula
                        pass
                    else:
                        bad_child_tag(child_tag)
                self.sheet.put_cell(rowx, colx, XL_CELL_BOOLEAN, cnv_xsd_boolean(tvalue), xf_index)
            elif cell_type == "e":
                # e = error
                # <v> child contains e.g. "#REF!"
                tvalue = '#N/A'
                for child in cell_elem:
                    child_tag = child.tag
                    if child_tag == V_TAG:
                        tvalue = child.text
                    elif child_tag == F_TAG:
                        # formula
                        pass
                    else:
                        bad_child_tag(child_tag)
                value = error_code_from_text[tvalue]
                self.sheet.put_cell(rowx, colx, XL_CELL_ERROR, value, xf_index)
            elif cell_type == "inlineStr":
                # Not expected in files produced by Excel.
                # It's a way of allowing 3rd party s/w to write text (including rich text) cells
                # without having to build a shared string table
                for child in cell_elem:
                    child_tag = child.tag
                    if child_tag == IS_TAG:
                        tvalue = get_text_from_si_or_is(self, child)
                    elif child_tag == V_TAG:
                        tvalue = child.text
                    elif child_tag == F_TAG:
                        # formula
                        pass
                    else:
                        bad_child_tag(child_tag)
                if not tvalue:
                    if self.bk.formatting_info:
                        self.sheet.put_cell(rowx, colx, XL_CELL_BLANK, '', xf_index)
                else:
                    self.sheet.put_cell(rowx, colx, XL_CELL_TEXT, tvalue, xf_index)
            else:
                raise Exception("Unknown cell type %r in rowx=%d colx=%d" % (cell_type, rowx, colx))

    tag2meth = {
        'row':          do_row,
    }
    augment_keys(tag2meth, U_SSML12)

def open_workbook_2007_xml(zf,
                           component_names,
                           logfile=sys.stdout,
                           verbosity=0,
                           use_mmap=0,
                           formatting_info=0,
                           on_demand=0,
                           ragged_rows=0):
    ensure_elementtree_imported(verbosity, logfile)
    bk = Book()
    bk.logfile = logfile
    bk.verbosity = verbosity
    bk.formatting_info = formatting_info
    if formatting_info:
        raise NotImplementedError("formatting_info=True not yet implemented")
    bk.use_mmap = False #### Not supported initially
    bk.on_demand = on_demand
    if on_demand:
        if verbosity:
            print("WARNING *** on_demand=True not yet implemented; falling back to False", file=bk.logfile)
        bk.on_demand = False
    bk.ragged_rows = ragged_rows

    x12book = X12Book(bk, logfile, verbosity)
    zflo = zf.open(component_names['xl/_rels/workbook.xml.rels'])
    x12book.process_rels(zflo)
    del zflo
    zflo = zf.open(component_names['xl/workbook.xml'])
    x12book.process_stream(zflo, 'Workbook')
    del zflo
    props_name = 'docprops/core.xml'
    if props_name in component_names:
        zflo = zf.open(component_names[props_name])
        x12book.process_coreprops(zflo)

    x12sty = X12Styles(bk, logfile, verbosity)
    if 'xl/styles.xml' in component_names:
        zflo = zf.open(component_names['xl/styles.xml'])
        x12sty.process_stream(zflo, 'styles')
        del zflo
    else:
        # seen in MS sample file MergedCells.xlsx
        pass

    sst_fname = 'xl/sharedstrings.xml'
    x12sst = X12SST(bk, logfile, verbosity)
    if sst_fname in component_names:
        zflo = zf.open(component_names[sst_fname])
        x12sst.process_stream(zflo, 'SST')
        del zflo

    for sheetx in range(bk.nsheets):
        fname = x12book.sheet_targets[sheetx]
        zflo = zf.open(component_names[fname])
        sheet = bk._sheet_list[sheetx]
        x12sheet = X12Sheet(sheet, logfile, verbosity)
        heading = "Sheet %r (sheetx=%d) from %r" % (sheet.name, sheetx, fname)
        x12sheet.process_stream(zflo, heading)
        del zflo

        rels_fname = 'xl/worksheets/_rels/%s.rels' % fname.rsplit('/', 1)[-1]
        if rels_fname in component_names:
            zfrels = zf.open(rels_fname)
            x12sheet.process_rels(zfrels)
            del zfrels

        for relid, reltype in x12sheet.relid2reltype.items():
            if reltype == 'comments':
                comments_fname = x12sheet.relid2path.get(relid)
                if comments_fname and comments_fname in component_names:
                    comments_stream = zf.open(comments_fname)
                    x12sheet.process_comments_stream(comments_stream)
                    del comments_stream

        sheet.tidy_dimensions()

    return bk
