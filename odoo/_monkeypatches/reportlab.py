
def patch_reportlab():
    # ---------------------------------------------------------
    # ReportLab's Data Matrix C40 encoder does not implement the
    # end-of-data rules from ISO/IEC 16022 §7.2.5.3.
    #
    # In particular, it always:
    #   - pads incomplete triplets with Shift 1
    #   - always emits an unlatch (254)
    #
    # The Data Matrix specification requires different behaviour
    # depending on both the remaining C40 values and the remaining
    # symbol codewords.
    #
    # This patch replaces _encode_c40() with a spec-compliant
    # implementation.
    # ---------------------------------------------------------

    def _encode_c40(self, value):
        encoded = []

        for c in value:
            encoded += self._encode_c40_char(c)

        codewords = []
        codewords.append(230) # Switch to C40 encoding

        remains = len(encoded) % 3

        final_ascii_character = False
        if remains == 1:
            encoded.pop()
            final_ascii_character = True
        if remains == 2:
            encoded.append(0)

        i = 0
        while i + 2 < len(encoded):
            chunk = encoded[i:i+3]
            total = chunk[0] * 1600 + chunk[1] * 40 + chunk[2] + 1
            codewords.append(total // 256)
            codewords.append(total % 256)
            i += 3

        remaining_space = self.cw_data - len(codewords)
        if remaining_space > 1:
            codewords.append(254)
        if final_ascii_character:
            codewords.append(ord(value[-1]) + 1)

        # Symbol capacity validation
        if len(codewords) > self.cw_data:
            raise Exception('Too much data to fit into a data matrix of this size')

        # Standard DataMatrix pseudo-random padding generation
        if len(codewords) < self.cw_data:
            codewords.append(129) # Start padding
            while len(codewords) < self.cw_data:
                r = ((149 * (len(codewords) + 1)) % 253) + 1
                codewords.append((129 + r) % 254)

        return codewords

    def patch_encoding_c40():
        try:
            from reportlab.graphics.barcode import ecc200datamatrix
        except ImportError:
            return  # nothing to patch
        ecc200datamatrix.ECC200DataMatrix._encode_c40 = _encode_c40

    patch_encoding_c40()
