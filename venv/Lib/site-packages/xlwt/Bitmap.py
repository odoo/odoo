# -*- coding: windows-1251 -*-

#  Portions are Copyright (C) 2005 Roman V. Kiseliov
#  Portions are Copyright (c) 2004 Evgeny Filatov <fufff@users.sourceforge.net>
#  Portions are Copyright (c) 2002-2004 John McNamara (Perl Spreadsheet::WriteExcel)

from .BIFFRecords import BiffRecord
from struct import pack, unpack


def _size_col(sheet, col):
    return sheet.col_width(col)


def _size_row(sheet, row):
    return sheet.row_height(row)


def _position_image(sheet, row_start, col_start, x1, y1, width, height):
    """Calculate the vertices that define the position of the image as required by
    the OBJ record.

             +------------+------------+
             |     A      |      B     |
       +-----+------------+------------+
       |     |(x1,y1)     |            |
       |  1  |(A1)._______|______      |
       |     |    |              |     |
       |     |    |              |     |
       +-----+----|    BITMAP    |-----+
       |     |    |              |     |
       |  2  |    |______________.     |
       |     |            |        (B2)|
       |     |            |     (x2,y2)|
       +---- +------------+------------+

    Example of a bitmap that covers some of the area from cell A1 to cell B2.

    Based on the width and height of the bitmap we need to calculate 8 vars:
        col_start, row_start, col_end, row_end, x1, y1, x2, y2.
    The width and height of the cells are also variable and have to be taken into
    account.
    The values of col_start and row_start are passed in from the calling
    function. The values of col_end and row_end are calculated by subtracting
    the width and height of the bitmap from the width and height of the
    underlying cells.
    The vertices are expressed as a percentage of the underlying cell width as
    follows (rhs values are in pixels):

           x1 = X / W *1024
           y1 = Y / H *256
           x2 = (X-1) / W *1024
           y2 = (Y-1) / H *256

           Where:  X is distance from the left side of the underlying cell
                   Y is distance from the top of the underlying cell
                   W is the width of the cell
                   H is the height of the cell

    Note: the SDK incorrectly states that the height should be expressed as a
    percentage of 1024.

    col_start  - Col containing upper left corner of object
    row_start  - Row containing top left corner of object
    x1  - Distance to left side of object
    y1  - Distance to top of object
    width  - Width of image frame
    height  - Height of image frame

    """
    # Adjust start column for offsets that are greater than the col width
    while x1 >= _size_col(sheet, col_start):
        x1 -= _size_col(sheet, col_start)
        col_start += 1
    # Adjust start row for offsets that are greater than the row height
    while y1 >= _size_row(sheet, row_start):
        y1 -= _size_row(sheet, row_start)
        row_start += 1
    # Initialise end cell to the same as the start cell
    row_end = row_start   # Row containing bottom right corner of object
    col_end = col_start   # Col containing lower right corner of object
    width = width + x1 - 1
    height = height + y1 - 1
    # Subtract the underlying cell widths to find the end cell of the image
    while (width >= _size_col(sheet, col_end)):
        width -= _size_col(sheet, col_end)
        col_end += 1
    # Subtract the underlying cell heights to find the end cell of the image
    while (height >= _size_row(sheet, row_end)):
        height -= _size_row(sheet, row_end)
        row_end += 1
    # Bitmap isn't allowed to start or finish in a hidden cell, i.e. a cell
    # with zero height or width.
    if ((_size_col(sheet, col_start) == 0) or (_size_col(sheet, col_end) == 0)
            or (_size_row(sheet, row_start) == 0) or (_size_row(sheet, row_end) == 0)):
        return
    # Convert the pixel values to the percentage value expected by Excel
    x1 = int(float(x1) / _size_col(sheet, col_start) * 1024)
    y1 = int(float(y1) / _size_row(sheet, row_start) * 256)
    # Distance to right side of object
    x2 = int(float(width) / _size_col(sheet, col_end) * 1024)
    # Distance to bottom of object
    y2 = int(float(height) / _size_row(sheet, row_end) * 256)
    return (col_start, x1, row_start, y1, col_end, x2, row_end, y2)


class ObjBmpRecord(BiffRecord):
    _REC_ID = 0x005D    # Record identifier

    def __init__(self, row, col, sheet, im_data_bmp, x, y, scale_x, scale_y):
        # Scale the frame of the image.
        width = im_data_bmp.width * scale_x
        height = im_data_bmp.height * scale_y

        # Calculate the vertices of the image and write the OBJ record
        coordinates = _position_image(sheet, row, col, x, y, width, height)
        # print coordinates
        col_start, x1, row_start, y1, col_end, x2, row_end, y2 = coordinates

        """Store the OBJ record that precedes an IMDATA record. This could be generalise
        to support other Excel objects.

        """
        cObj = 0x0001      # Count of objects in file (set to 1)
        OT = 0x0008        # Object type. 8 = Picture
        id = 0x0001        # Object ID
        grbit = 0x0614     # Option flags
        colL = col_start    # Col containing upper left corner of object
        dxL = x1            # Distance from left side of cell
        rwT = row_start     # Row containing top left corner of object
        dyT = y1            # Distance from top of cell
        colR = col_end      # Col containing lower right corner of object
        dxR = x2            # Distance from right of cell
        rwB = row_end       # Row containing bottom right corner of object
        dyB = y2            # Distance from bottom of cell
        cbMacro = 0x0000    # Length of FMLA structure
        Reserved1 = 0x0000  # Reserved
        Reserved2 = 0x0000  # Reserved
        icvBack = 0x09      # Background colour
        icvFore = 0x09      # Foreground colour
        fls = 0x00          # Fill pattern
        fAuto = 0x00        # Automatic fill
        icv = 0x08          # Line colour
        lns = 0xff          # Line style
        lnw = 0x01          # Line weight
        fAutoB = 0x00       # Automatic border
        frs = 0x0000        # Frame style
        cf = 0x0009         # Image format, 9 = bitmap
        Reserved3 = 0x0000  # Reserved
        cbPictFmla = 0x0000 # Length of FMLA structure
        Reserved4 = 0x0000  # Reserved
        grbit2 = 0x0001     # Option flags
        Reserved5 = 0x0000  # Reserved

        data = pack("<L", cObj)
        data += pack("<H", OT)
        data += pack("<H", id)
        data += pack("<H", grbit)
        data += pack("<H", colL)
        data += pack("<H", dxL)
        data += pack("<H", rwT)
        data += pack("<H", dyT)
        data += pack("<H", colR)
        data += pack("<H", dxR)
        data += pack("<H", rwB)
        data += pack("<H", dyB)
        data += pack("<H", cbMacro)
        data += pack("<L", Reserved1)
        data += pack("<H", Reserved2)
        data += pack("<B", icvBack)
        data += pack("<B", icvFore)
        data += pack("<B", fls)
        data += pack("<B", fAuto)
        data += pack("<B", icv)
        data += pack("<B", lns)
        data += pack("<B", lnw)
        data += pack("<B", fAutoB)
        data += pack("<H", frs)
        data += pack("<L", cf)
        data += pack("<H", Reserved3)
        data += pack("<H", cbPictFmla)
        data += pack("<H", Reserved4)
        data += pack("<H", grbit2)
        data += pack("<L", Reserved5)

        self._rec_data = data

def _process_bitmap(bitmap):
    """Convert a 24 bit bitmap into the modified internal format used by Windows.
    This is described in BITMAPCOREHEADER and BITMAPCOREINFO structures in the
    MSDN library.

    """
    # Open file and binmode the data in case the platform needs it.
    with open(bitmap, "rb") as fh:
        # Slurp the file into a string.
        data = fh.read()
    return _process_bitmap_data(data)

def _process_bitmap_data(data):
    # Check that the file is big enough to be a bitmap.
    if len(data) <= 0x36:
        raise Exception("bitmap doesn't contain enough data.")
    # The first 2 bytes are used to identify the bitmap.
    if (data[:2] != b"BM"):
        raise Exception("bitmap doesn't appear to to be a valid bitmap image.")
    # Remove bitmap data: ID.
    data = data[2:]
    # Read and remove the bitmap size. This is more reliable than reading
    # the data size at offset 0x22.
    #
    size = unpack("<L", data[:4])[0]
    size -=  0x36   # Subtract size of bitmap header.
    size +=  0x0C   # Add size of BIFF header.
    data = data[4:]
    # Remove bitmap data: reserved, offset, header length.
    data = data[12:]
    # Read and remove the bitmap width and height. Verify the sizes.
    width, height = unpack("<LL", data[:8])
    data = data[8:]
    if (width > 0xFFFF):
        raise Exception("bitmap: largest image width supported is 65k.")
    if (height > 0xFFFF):
        raise Exception("bitmap: largest image height supported is 65k.")
    # Read and remove the bitmap planes and bpp data. Verify them.
    planes, bitcount = unpack("<HH", data[:4])
    data = data[4:]
    if (bitcount != 24):
        raise Exception("bitmap isn't a 24bit true color bitmap.")
    if (planes != 1):
        raise Exception("bitmap: only 1 plane supported in bitmap image.")
    # Read and remove the bitmap compression. Verify compression.
    compression = unpack("<L", data[:4])[0]
    data = data[4:]
    if (compression != 0):
        raise Exception("bitmap: compression not supported in bitmap image.")
    # Remove bitmap data: data size, hres, vres, colours, imp. colours.
    data = data[20:]
    # Add the BITMAPCOREHEADER data
    header = pack("<LHHHH", 0x000c, width, height, 0x01, 0x18)
    data = header + data
    return (width, height, size, data)


class ImRawDataBmpRecord(BiffRecord):
    _REC_ID = 0x007F

    def __init__(self, data):
        """Insert a 24bit bitmap image in a worksheet. The main record required is
        IMDATA but it must be proceeded by a OBJ record to define its position.

        """
        BiffRecord.__init__(self)

        self.width, self.height, self.size, data = _process_bitmap_data(data)
        self._write_imdata(data)

    def _write_imdata(self, data):
        # Write the IMDATA record to store the bitmap data
        cf = 0x09
        env = 0x01
        lcb = self.size
        self._rec_data = pack("<HHL", cf, env, lcb) + data

class ImDataBmpRecord(ImRawDataBmpRecord):
    def __init__(self, filename):
        """Insert a 24bit bitmap image in a worksheet. The main record required is
        IMDATA but it must be proceeded by a OBJ record to define its position.

        """
        BiffRecord.__init__(self)

        self.width, self.height, self.size, data = _process_bitmap(filename)
        self._write_imdata(data)

