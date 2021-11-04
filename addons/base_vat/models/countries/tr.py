import stdnum
from odoo import models


# TODO seems to be considering both VKN and TIN whereas it is not the case for stdnum
# https://github.com/odoo/odoo/commit/58e38aeb17881076362fac482185b06331037317
class VatCheck(models.AbstractModel):
    _inherit = 'base.vat.mixin'

    # VAT validation in Turkey, contributed by # Levent Karakas @ Eska Yazilim A.S.
    def check_vat_tr(self, vat):

        if not (10 <= len(vat) <= 11):
            raise stdnum.exceptions.InvalidLength
        try:
            int(vat)
        except ValueError:
            raise stdnum.exceptions.InvalidFormat

        # check vat number (vergi no)
        if len(vat) == 10:
            summed = 0
            check = 0
            for f in range(0, 9):
                c1 = (int(vat[f]) + (9-f)) % 10
                c2 = (c1 * (2 ** (9-f))) % 9
                if (c1 != 0) and (c2 == 0):
                    c2 = 9
                summed += c2
            if summed % 10 == 0:
                check = 0
            else:
                check = 10 - (summed % 10)
            if int(vat[9]) == check:
                return True

        # check personal id (tc kimlik no)
        if len(vat) == 11:
            c1a = 0
            c1b = 0
            c2 = 0
            for f in range(0, 9, 2):
                c1a += int(vat[f])
            for f in range(1, 9, 2):
                c1b += int(vat[f])
            c1 = ((7 * c1a) - c1b) % 10
            for f in range(0, 10):
                c2 += int(vat[f])
            c2 = c2 % 10
            if int(vat[9]) == c1 and int(vat[10]) == c2:
                return True

        raise stdnum.exceptions.InvalidChecksum
