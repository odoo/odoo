# -*- coding: windows-1252 -*-

from .BIFFRecords import ColInfoRecord

class Column(object):
    def __init__(self, colx, parent_sheet):
        if not(isinstance(colx, int) and 0 <= colx <= 255):
            raise ValueError("column index (%r) not an int in range(256)" % colx)
        self._index = colx
        self._parent = parent_sheet
        self._parent_wb = parent_sheet.get_parent()
        self._xf_index = 0x0F

        self.width = 0x0B92
        self.hidden = 0
        self.level = 0
        self.collapse = 0
        self.user_set = 0
        self.best_fit = 0
        self.unused = 0
        
    def set_width(self, width):
        if not(isinstance(width, int) and 0 <= width <= 65535):
            raise ValueError("column width (%r) not an int in range(65536)" % width)
        self._width = width

    def get_width(self):
        return self._width

    width = property(get_width, set_width)

    def set_style(self, style):
        self._xf_index = self._parent_wb.add_style(style)

    def width_in_pixels(self):
        # *** Approximation ****
        return int(round(self.width * 0.0272 + 0.446, 0))

    def get_biff_record(self):
        options =  (self.hidden & 0x01) << 0
        options |= (self.user_set & 0x01) << 1
        options |= (self.best_fit & 0x01) << 2
        options |= (self.level & 0x07) << 8
        options |= (self.collapse & 0x01) << 12

        return ColInfoRecord(self._index, self._index, self.width, self._xf_index, options, self.unused).get()



