#this code contributed by Kyle Macfarlane see
#https://bitbucket.org/rptlab/reportlab/issues/69/implementations-of-code-128-auto-and-data
__all__= ('ECC200datamatrix',)
FACTORS = {
    5: (228, 48, 15, 111, 62),
    7: (23, 68, 144, 134, 240, 92, 254),
    10: (28, 24, 185, 166, 223, 248, 116, 255, 110, 61),
    11: (175, 138, 205, 12, 194, 168, 39, 245, 60, 97, 120),
    12: (41, 153, 158, 91, 61, 42, 142, 213, 97, 178, 100, 242),
    14: (156, 97, 192, 252, 95, 9, 157, 119, 138, 45, 18, 186, 83, 185),
    18: (83, 195, 100, 39, 188, 75, 66, 61, 241, 213, 109, 129,
         94, 254, 225, 48, 90, 188),
    20: (15, 195, 244, 9, 233, 71, 168, 2, 188, 160, 153, 145,
         253, 79, 108, 82, 27, 174, 186, 172),
    24: (52, 190, 88, 205, 109, 39, 176, 21, 155, 197, 251, 223, 155,
         21, 5, 172, 254, 124, 12, 181, 184, 96, 50, 193),
    28: (211, 231, 43, 97, 71, 96, 103, 174, 37, 151, 170, 53, 75, 34,
         249, 121, 17, 138, 110, 213, 141, 136, 120, 151, 233, 168, 93, 255),
    36: (245, 127, 242, 218, 130, 250, 162, 181, 102, 120, 84, 179, 220, 251,
         80, 182, 229, 18, 2, 4, 68, 33, 101, 137, 95, 119, 115, 44,
         175, 184, 59, 25, 225, 98, 81, 112),
    42: (77, 193, 137, 31, 19, 38, 22, 153, 247, 105, 122, 2, 245, 133,
         242, 8, 175, 95, 100, 9, 167, 105, 214, 111, 57, 121, 21,
         1, 253, 57, 54, 101, 248, 202, 69, 50, 150, 177, 226, 5, 9, 5),
    48: (245, 132, 172, 223, 96, 32, 117, 22, 238, 133, 238, 231, 205, 188,
         237, 87, 191, 106, 16, 147, 118, 23, 37, 90, 170, 205, 131, 88,
         120, 100, 66, 138, 186, 240, 82, 44, 176, 87, 187, 147, 160, 175,
         69, 213, 92, 253, 225, 19),
    56: (175, 9, 223, 238, 12, 17, 220, 208, 100, 29, 175, 170, 230, 192,
         215, 235, 150, 159, 36, 223, 38, 200, 132, 54, 228, 146, 218, 234,
         117, 203, 29, 232, 144, 238, 22, 150, 201, 117, 62, 207, 164, 13,
         137, 245, 127, 67, 247, 28, 155, 43, 203, 107, 233, 53, 143, 46),
    62: (242, 93, 169, 50, 144, 210, 39, 118, 202, 188, 201, 189, 143, 108,
         196, 37, 185, 112, 134, 230, 245, 63, 197, 190, 250, 106, 185, 221,
         175, 64, 114, 71, 161, 44, 147, 6, 27, 218, 51, 63, 87, 10,
         40, 130, 188, 17, 163, 31, 176, 170, 4, 107, 232, 7, 94, 166,
         224, 124, 86, 47, 11, 204),
    68: (220, 228, 173, 89, 251, 149, 159, 56, 89, 33, 147, 244, 154, 36,
         73, 127, 213, 136, 248, 180, 234, 197, 158, 177, 68, 122, 93, 213,
         15, 160, 227, 236, 66, 139, 153, 185, 202, 167, 179, 25, 220, 232,
         96, 210, 231, 136, 223, 239, 181, 241, 59, 52, 172, 25, 49, 232,
         211, 189, 64, 54, 108, 153, 132, 63, 96, 103, 82, 186)
}

LOGVAL = (
    -255, 255, 1, 240, 2, 225, 241, 53, 3, 38, 226, 133, 242, 43,
    54, 210, 4, 195, 39, 114, 227, 106, 134, 28, 243, 140, 44, 23,
    55, 118, 211, 234, 5, 219, 196, 96, 40, 222, 115, 103, 228, 78,
    107, 125, 135, 8, 29, 162, 244, 186, 141, 180, 45, 99, 24, 49,
    56, 13, 119, 153, 212, 199, 235, 91, 6, 76, 220, 217, 197, 11,
    97, 184, 41, 36, 223, 253, 116, 138, 104, 193, 229, 86, 79, 171,
    108, 165, 126, 145, 136, 34, 9, 74, 30, 32, 163, 84, 245, 173,
    187, 204, 142, 81, 181, 190, 46, 88, 100, 159, 25, 231, 50, 207,
    57, 147, 14, 67, 120, 128, 154, 248, 213, 167, 200, 63, 236, 110,
    92, 176, 7, 161, 77, 124, 221, 102, 218, 95, 198, 90, 12, 152,
    98, 48, 185, 179, 42, 209, 37, 132, 224, 52, 254, 239, 117, 233,
    139, 22, 105, 27, 194, 113, 230, 206, 87, 158, 80, 189, 172, 203,
    109, 175, 166, 62, 127, 247, 146, 66, 137, 192, 35, 252, 10, 183,
    75, 216, 31, 83, 33, 73, 164, 144, 85, 170, 246, 65, 174, 61,
    188, 202, 205, 157, 143, 169, 82, 72, 182, 215, 191, 251, 47, 178,
    89, 151, 101, 94, 160, 123, 26, 112, 232, 21, 51, 238, 208, 131,
    58, 69, 148, 18, 15, 16, 68, 17, 121, 149, 129, 19, 155, 59,
    249, 70, 214, 250, 168, 71, 201, 156, 64, 60, 237, 130, 111, 20,
    93, 122, 177, 150
)

ALOGVAL = (
    1, 2, 4, 8, 16, 32, 64, 128, 45, 90, 180, 69, 138, 57,
    114, 228, 229, 231, 227, 235, 251, 219, 155, 27, 54, 108, 216, 157,
    23, 46, 92, 184, 93, 186, 89, 178, 73, 146, 9, 18, 36, 72,
    144, 13, 26, 52, 104, 208, 141, 55, 110, 220, 149, 7, 14, 28,
    56, 112, 224, 237, 247, 195, 171, 123, 246, 193, 175, 115, 230, 225,
    239, 243, 203, 187, 91, 182, 65, 130, 41, 82, 164, 101, 202, 185,
    95, 190, 81, 162, 105, 210, 137, 63, 126, 252, 213, 135, 35, 70,
    140, 53, 106, 212, 133, 39, 78, 156, 21, 42, 84, 168, 125, 250,
    217, 159, 19, 38, 76, 152, 29, 58, 116, 232, 253, 215, 131, 43,
    86, 172, 117, 234, 249, 223, 147, 11, 22, 44, 88, 176, 77, 154,
    25, 50, 100, 200, 189, 87, 174, 113, 226, 233, 255, 211, 139, 59,
    118, 236, 245, 199, 163, 107, 214, 129, 47, 94, 188, 85, 170, 121,
    242, 201, 191, 83, 166, 97, 194, 169, 127, 254, 209, 143, 51, 102,
    204, 181, 71, 142, 49, 98, 196, 165, 103, 206, 177, 79, 158, 17,
    34, 68, 136, 61, 122, 244, 197, 167, 99, 198, 161, 111, 222, 145,
    15, 30, 60, 120, 240, 205, 183, 67, 134, 33, 66, 132, 37, 74,
    148, 5, 10, 20, 40, 80, 160, 109, 218, 153, 31, 62, 124, 248,
    221, 151, 3, 6, 12, 24, 48, 96, 192, 173, 119, 238, 241, 207,
    179, 75, 150, 1
)

from reportlab.graphics.barcode.common import Barcode
class ECC200DataMatrix(Barcode):
    '''This code only supports a Type 12 (44x44) C40 encoded data matrix.
    This is the size and encoding that Royal Mail wants on all mail from October 1st 2015.
    see https://bitbucket.org/rptlab/reportlab/issues/69/implementations-of-code-128-auto-and-data
    '''
    barWidth = 4

    def __init__(self, *args, **kwargs):
        Barcode.__init__(self,*args, **kwargs)

        # These values below are hardcoded for a Type 12 44x44 data matrix
        self.row_modules = 44
        self.col_modules = 44
        self.row_regions = 2
        self.col_regions = 2
        self.cw_data = 144
        self.cw_ecc = 56
        self.row_usable_modules = self.row_modules - self.row_regions * 2
        self.col_usable_modules = self.col_modules - self.col_regions * 2

    def validate(self):
        self.valid = 1
        for c in self.value:
            if ord(c) > 255:
                self.valid = 0
                break
        else:
            self.validated = self.value

    def _encode_c40_char(self, char):
        o = ord(char)
        encoded = []

        if o == 32 or (o >= 48 and o <= 57) or (o >= 65 and o <= 90):
            # Stay in set 0
            if o == 32:
                encoded.append(o - 29)
            elif o >= 48 and o <= 57:
                encoded.append(o - 44)
            else:
                encoded.append(o - 51)
        elif o >= 0 and o <= 31:
            encoded.append(0) # Shift to set 1
            encoded.append(o)
        elif (o >= 33 and o <= 64) or (o >= 91 and o <= 95):
            encoded.append(1) # Shift to set 2
            if o >= 33 and o <= 64:
                encoded.append(o - 33)
            else:
                encoded.append(o - 69)
        elif o >= 96 and o <= 127:
            encoded.append(2) # Shift to set 3
            encoded.append(o - 96)
        elif o >= 128 and o <= 255:
            # Extended ASCII
            encoded.append(1) # Shift to set 2
            encoded.append(30) # Upper shift / hibit
            encoded += self._encode_c40_char(chr(o - 128))
        else:
            raise Exception('Cannot encode %s (%s)' % (char, o))

        return encoded

    def _encode_c40(self, value):
        encoded = []

        for c in value:
            encoded += self._encode_c40_char(c)

        while len(encoded) % 3:
            encoded.append(0) # Fake padding that makes chunking in the next step easier

        codewords = []
        codewords.append(230) # Switch to C40 encoding

        for i in range(0, len(encoded), 3):
            chunk = encoded[i:i+3]
            total = chunk[0] * 1600 + chunk[1] * 40 + chunk[2] + 1
            codewords.append(total // 256)
            codewords.append(total % 256)

        codewords.append(254) # End of data

        if len(codewords) > self.cw_data:
            raise Exception('Too much data to fit into a data matrix of this size')

        if len(codewords) < self.cw_data:
            # Real padding
            codewords.append(129) # Start padding
            while len(codewords) < self.cw_data:
                r = ((149 * (len(codewords) + 1)) % 253) + 1
                codewords.append((129 + r) % 254)

        return codewords

    def _gfsum(self, int1, int2):
        return int1 ^ int2

    def _gfproduct(self, int1, int2):
        if int1 == 0 or int2 == 0:
            return 0
        else:
            return ALOGVAL[(LOGVAL[int1] + LOGVAL[int2]) % 255]

    def _get_reed_solomon_code(self, data, num_code_words):
        """
        This method is basically verbatim from "huBarcode" which is BSD licensed
        https://github.com/hudora/huBarcode/blob/master/hubarcode/datamatrix/reedsolomon.py
        """
        cw_factors = FACTORS[num_code_words]
        code_words = [0] * num_code_words

        for data_word in data:
            tmp = self._gfsum(data_word, code_words[-1])
            for j in range(num_code_words - 1, -1, -1):
                code_words[j] = self._gfproduct(tmp, cw_factors[j])
                if j > 0:
                    code_words[j] = self._gfsum(code_words[j - 1], code_words[j])

        code_words.reverse()
        return code_words

    def _get_next_bits(self, data):
        value = data.pop(0)
        bits = []
        for i in range(0, 8):
            bits.append(value >> i & 1)
        bits.reverse()
        return bits

    def _place_bit(self, row, col, bit):
        if row < 0:
            row += self.row_usable_modules
            col += (4 - ((self.row_usable_modules + 4) % 8))

        if col < 0:
            col += self.col_usable_modules
            row += (4 - ((self.col_usable_modules + 4) % 8))

        self._matrix[row][col] = bit

    def _place_bit_corner_1(self, data):
        bits = self._get_next_bits(data)
        self._place_bit(self.row_usable_modules - 1, 0, bits[0])
        self._place_bit(self.row_usable_modules - 1, 1, bits[1])
        self._place_bit(self.row_usable_modules - 1, 2, bits[2])
        self._place_bit(0, self.col_usable_modules - 2, bits[3])
        self._place_bit(0, self.col_usable_modules - 1, bits[4])
        self._place_bit(1, self.col_usable_modules - 1, bits[5])
        self._place_bit(2, self.col_usable_modules - 1, bits[6])
        self._place_bit(3, self.col_usable_modules - 1, bits[7])

    def _place_bit_corner_2(self, data):
        bits = self._get_next_bits(data)
        self._place_bit(self.row_usable_modules - 3, 0, bits[0])
        self._place_bit(self.row_usable_modules - 2, 0, bits[1])
        self._place_bit(self.row_usable_modules - 1, 0, bits[2])
        self._place_bit(0, self.col_usable_modules - 4, bits[3])
        self._place_bit(0, self.col_usable_modules - 3, bits[4])
        self._place_bit(0, self.col_usable_modules - 2, bits[5])
        self._place_bit(0, self.col_usable_modules - 1, bits[6])
        self._place_bit(1, self.col_usable_modules - 1, bits[7])

    def _place_bit_corner_3(self, data):
        bits = self._get_next_bits(data)
        self._place_bit(self.row_usable_modules - 3, 0, bits[0])
        self._place_bit(self.row_usable_modules - 2, 0, bits[1])
        self._place_bit(self.row_usable_modules - 1, 0, bits[2])
        self._place_bit(0, self.col_usable_modules - 2, bits[3])
        self._place_bit(0, self.col_usable_modules - 1, bits[4])
        self._place_bit(1, self.col_usable_modules - 1, bits[5])
        self._place_bit(2, self.col_usable_modules - 1, bits[6])
        self._place_bit(3, self.col_usable_modules - 1, bits[7])

    def _place_bit_corner_4(self, data):
        bits = self._get_next_bits(data)
        self._place_bit(self.row_usable_modules - 1, 0, bits[0])
        self._place_bit(self.row_usable_modules - 1, self.col_usable_modules - 1, bits[1])
        self._place_bit(0, self.col_usable_modules - 3, bits[2])
        self._place_bit(0, self.col_usable_modules - 2, bits[3])
        self._place_bit(0, self.col_usable_modules - 1, bits[4])
        self._place_bit(1, self.col_usable_modules - 3, bits[5])
        self._place_bit(1, self.col_usable_modules - 2, bits[6])
        self._place_bit(1, self.col_usable_modules - 1, bits[7])

    def _place_bit_standard(self, data, row, col):
        bits = self._get_next_bits(data)
        self._place_bit(row - 2, col - 2, bits[0])
        self._place_bit(row - 2, col - 1, bits[1])
        self._place_bit(row - 1, col - 2, bits[2])
        self._place_bit(row - 1, col - 1, bits[3])
        self._place_bit(row - 1, col, bits[4])
        self._place_bit(row, col - 2, bits[5])
        self._place_bit(row, col - 1, bits[6])
        self._place_bit(row, col, bits[7])

    def _create_matrix(self, data):
        """
        This method is heavily influenced by "huBarcode" which is BSD licensed
        https://github.com/hudora/huBarcode/blob/master/hubarcode/datamatrix/placement.py
        """
        rows = self.row_usable_modules
        cols = self.col_usable_modules

        self._matrix = self._create_empty_matrix(rows, cols)

        row = 4
        col = 0

        while True:
            if row == rows and col == 0:
                self._place_bit_corner_1(data)
            elif row == (rows - 2) and col == 0 and (cols % 4):
                self._place_bit_corner_2(data)
            elif row == (rows - 2) and col == 0 and (cols % 8 == 4):
                self._place_bit_corner_3(data)
            elif row == (rows + 4) and col == 2 and (cols % 8 == 0):
                self._place_bit_corner_4(data)

            while True:
                if row < rows and col >= 0 and self._matrix[row][col] is None:
                    self._place_bit_standard(data, row, col)

                row -= 2
                col += 2

                if row < 0 or col >= cols:
                    break

            row += 1
            col += 3

            while True:
                if row >= 0 and col < cols and self._matrix[row][col] is None:
                    self._place_bit_standard(data, row, col)

                row += 2
                col -= 2

                if row >= rows or col < 0:
                    break

            row += 3
            col += 1

            if row >= rows and col >= cols:
                break

        for row in self._matrix:
            for i in range(0, cols):
                if row[i] is None:
                    row[i] = 0

        return self._matrix

    def _create_data_regions(self, matrix):
        regions = []
        col_offset = 0
        row_offset = 0

        rows = int(self.row_usable_modules / self.row_regions)
        cols = int(self.col_usable_modules / self.col_regions)

        while col_offset < self.row_regions:
            while row_offset < self.col_regions:
                r_offset = col_offset * rows
                c_offset = row_offset * cols
                region = matrix[r_offset:rows+r_offset]
                for i in range(0, len(region)):
                    region[i] = region[i][c_offset:cols+c_offset]
                regions.append(region)
                row_offset += 1
            row_offset = 0
            col_offset += 1

        return regions

    def _create_empty_matrix(self, row, col):
        matrix = []
        for i in range(0, row):
            matrix.append([None] * col)
        return matrix

    def _wrap_data_regions_with_finders(self, regions):
        wrapped = []

        for region in regions:
            matrix = self._create_empty_matrix(
                int(self.col_modules / self.col_regions),
                int(self.row_modules / self.row_regions)
            )

            for i, rows in enumerate(region):
                for j, data in enumerate(rows):
                    matrix[i+1][j+1] = data

            for i, row in enumerate(matrix):
                if i == 0:
                    for j, col in enumerate(row):
                        row[j] = (j + 1) % 2
                elif i + 1 == len(matrix):
                    for j, col in enumerate(row):
                        row[j] = 1
                else:
                    row[0] = 1
                    row[-1] = i % 2

            wrapped.append(matrix)

        return wrapped

    def _merge_data_regions(self, regions):
        merged = []

        for i in range(0, len(regions), self.row_regions):
            chunk = regions[i:i+self.row_regions]
            j = 0
            while j < len(chunk[0]):
                merged_row = []
                for row in chunk:
                    merged_row += row[j]
                merged.append(merged_row)
                j += 1

        return merged

    def encode(self):
        if hasattr(self, 'encoded'):
            return self.encoded

        encoded = self._encode_c40(self.validated)
        encoded += self._get_reed_solomon_code(encoded, self.cw_ecc)

        matrix = self._create_matrix(encoded)
        data_regions = self._create_data_regions(matrix)
        wrapped = self._wrap_data_regions_with_finders(data_regions)
        self.encoded = self._merge_data_regions(wrapped)

        self.encoded.reverse() # Helpful since PDFs start at bottom left corner

        return self.encoded

    def computeSize(self, *args):
        self._height = self.row_modules * self.barWidth
        self._width = self.col_modules * self.barWidth

    def draw(self):
        for y, row in enumerate(self.encoded):
            for x, data in enumerate(row):
                if data:
                    self.rect(
                        self.x + x * self.barWidth,
                        self.y + y * self.barWidth,
                        self.barWidth,
                        self.barWidth
                    )
