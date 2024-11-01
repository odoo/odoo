# -*- coding: windows-1252 -*-

from struct import unpack, pack
from . import BIFFRecords
from .compat import xrange

class StrCell(object):
    __slots__ = ["rowx", "colx", "xf_idx", "sst_idx"]

    def __init__(self, rowx, colx, xf_idx, sst_idx):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx
        self.sst_idx = sst_idx

    def get_biff_data(self):
        # return BIFFRecords.LabelSSTRecord(self.rowx, self.colx, self.xf_idx, self.sst_idx).get()
        return pack('<5HL', 0x00FD, 10, self.rowx, self.colx, self.xf_idx, self.sst_idx)

class BlankCell(object):
    __slots__ = ["rowx", "colx", "xf_idx"]

    def __init__(self, rowx, colx, xf_idx):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx

    def get_biff_data(self):
        # return BIFFRecords.BlankRecord(self.rowx, self.colx, self.xf_idx).get()
        return pack('<5H', 0x0201, 6, self.rowx, self.colx, self.xf_idx)

class MulBlankCell(object):
    __slots__ = ["rowx", "colx1", "colx2", "xf_idx"]

    def __init__(self, rowx, colx1, colx2, xf_idx):
        self.rowx = rowx
        self.colx1 = colx1
        self.colx2 = colx2
        self.xf_idx = xf_idx

    def get_biff_data(self):
        return BIFFRecords.MulBlankRecord(self.rowx,
            self.colx1, self.colx2, self.xf_idx).get()

class NumberCell(object):
    __slots__ = ["rowx", "colx", "xf_idx", "number"]

    def __init__(self, rowx, colx, xf_idx, number):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx
        self.number = float(number)

    def get_encoded_data(self):
        rk_encoded = 0
        num = self.number

        # The four possible kinds of RK encoding are *not* mutually exclusive.
        # The 30-bit integer variety picks up the most.
        # In the code below, the four varieties are checked in descending order
        # of bangs per buck, or not at all.
        # SJM 2007-10-01

        if -0x20000000 <= num < 0x20000000: # fits in 30-bit *signed* int
            inum = int(num)
            if inum == num: # survives round-trip
                # print "30-bit integer RK", inum, hex(inum)
                rk_encoded = 2 | (inum << 2)
                return 1, rk_encoded

        temp = num * 100

        if -0x20000000 <= temp < 0x20000000:
            # That was step 1: the coded value will fit in
            # a 30-bit signed integer.
            itemp = int(round(temp, 0))
            # That was step 2: "itemp" is the best candidate coded value.
            # Now for step 3: simulate the decoding,
            # to check for round-trip correctness.
            if itemp / 100.0 == num:
                # print "30-bit integer RK*100", itemp, hex(itemp)
                rk_encoded = 3 | (itemp << 2)
                return 1, rk_encoded

        if 0: # Cost of extra pack+unpack not justified by tiny yield.
            packed = pack('<d', num)
            w01, w23 = unpack('<2i', packed)
            if not w01 and not(w23 & 3):
                # 34 lsb are 0
                # print "float RK", w23, hex(w23)
                return 1, w23

            packed100 = pack('<d', temp)
            w01, w23 = unpack('<2i', packed100)
            if not w01 and not(w23 & 3):
                # 34 lsb are 0
                # print "float RK*100", w23, hex(w23)
                return 1, w23 | 1

        #print "Number"
        #print
        return 0, pack('<5Hd', 0x0203, 14, self.rowx, self.colx, self.xf_idx, num)

    def get_biff_data(self):
        isRK, value = self.get_encoded_data()
        if isRK:
            return pack('<5Hi', 0x27E, 10, self.rowx, self.colx, self.xf_idx, value)
        return value # NUMBER record already packed

class BooleanCell(object):
    __slots__ = ["rowx", "colx", "xf_idx", "number"]

    def __init__(self, rowx, colx, xf_idx, number):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx
        self.number = number

    def get_biff_data(self):
        return BIFFRecords.BoolErrRecord(self.rowx,
            self.colx, self.xf_idx, self.number, 0).get()

error_code_map = {
    0x00:  0, # Intersection of two cell ranges is empty
    0x07:  7, # Division by zero
    0x0F: 15, # Wrong type of operand
    0x17: 23, # Illegal or deleted cell reference
    0x1D: 29, # Wrong function or range name
    0x24: 36, # Value range overflow
    0x2A: 42, # Argument or function not available
    '#NULL!' :  0, # Intersection of two cell ranges is empty
    '#DIV/0!':  7, # Division by zero
    '#VALUE!': 36, # Wrong type of operand
    '#REF!'  : 23, # Illegal or deleted cell reference
    '#NAME?' : 29, # Wrong function or range name
    '#NUM!'  : 36, # Value range overflow
    '#N/A!'  : 42, # Argument or function not available
}

class ErrorCell(object):
    __slots__ = ["rowx", "colx", "xf_idx", "number"]

    def __init__(self, rowx, colx, xf_idx, error_string_or_code):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx
        try:
            self.number = error_code_map[error_string_or_code]
        except KeyError:
            raise Exception('Illegal error value (%r)' % error_string_or_code)

    def get_biff_data(self):
        return BIFFRecords.BoolErrRecord(self.rowx,
            self.colx, self.xf_idx, self.number, 1).get()

class FormulaCell(object):
    __slots__ = ["rowx", "colx", "xf_idx", "frmla", "calc_flags"]

    def __init__(self, rowx, colx, xf_idx, frmla, calc_flags=0):
        self.rowx = rowx
        self.colx = colx
        self.xf_idx = xf_idx
        self.frmla = frmla
        self.calc_flags = calc_flags

    def get_biff_data(self):
        return BIFFRecords.FormulaRecord(self.rowx,
            self.colx, self.xf_idx, self.frmla.rpn(), self.calc_flags).get()

# module-level function for *internal* use by the Row module

def _get_cells_biff_data_mul(rowx, cell_items):
    # Return the BIFF data for all cell records in the row.
    # Adjacent BLANK|RK records are combined into MUL(BLANK|RK) records.
    pieces = []
    nitems = len(cell_items)
    i = 0
    while i < nitems:
        icolx, icell = cell_items[i]
        if isinstance(icell, NumberCell):
            isRK, value = icell.get_encoded_data()
            if not isRK:
                pieces.append(value) # pre-packed NUMBER record
                i += 1
                continue
            muldata = [(value, icell.xf_idx)]
            target = NumberCell
        elif isinstance(icell, BlankCell):
            muldata = [icell.xf_idx]
            target = BlankCell
        else:
            pieces.append(icell.get_biff_data())
            i += 1
            continue
        lastcolx = icolx
        j = i
        packed_record = ''
        for j in xrange(i+1, nitems):
            jcolx, jcell = cell_items[j]
            if jcolx != lastcolx + 1:
                nexti = j
                break
            if not isinstance(jcell, target):
                nexti = j
                break
            if target == NumberCell:
                isRK, value = jcell.get_encoded_data()
                if not isRK:
                    packed_record = value
                    nexti = j + 1
                    break
                muldata.append((value, jcell.xf_idx))
            else:
                muldata.append(jcell.xf_idx)
            lastcolx = jcolx
        else:
            nexti = j + 1
        if target == NumberCell:
            if lastcolx == icolx:
                # RK record
                value, xf_idx = muldata[0]
                pieces.append(pack('<5Hi', 0x027E, 10, rowx, icolx, xf_idx, value))
            else:
                # MULRK record
                nc = lastcolx - icolx + 1
                pieces.append(pack('<4H', 0x00BD, 6 * nc + 6, rowx, icolx))
                pieces.append(b''.join(pack('<Hi', xf_idx, value) for value, xf_idx in muldata))
                pieces.append(pack('<H', lastcolx))
        else:
            if lastcolx == icolx:
                # BLANK record
                xf_idx = muldata[0]
                pieces.append(pack('<5H', 0x0201, 6, rowx, icolx, xf_idx))
            else:
                # MULBLANK record
                nc = lastcolx - icolx + 1
                pieces.append(pack('<4H', 0x00BE, 2 * nc + 6, rowx, icolx))
                pieces.append(b''.join(pack('<H', xf_idx) for xf_idx in muldata))
                pieces.append(pack('<H', lastcolx))
        if packed_record:
            pieces.append(packed_record)
        i = nexti
    return b''.join(pieces)

