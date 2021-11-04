import re
import stdnum
from odoo import models

# https://github.com/arthurdejong/python-stdnum/commit/26a7e7bc5cdb6b2d69cbabfbf7d3011697ec3eeb
# Version 1.17
class VatCheck(models.AbstractModel):
    _inherit = 'base.vat.mixin'

    def check_vat_in(self, vat):
        #reference from https://www.gstzen.in/a/format-of-a-gst-number-gstin.html
        if vat and len(vat) == 15:
            all_gstin_re = [
                r'[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[Zz1-9A-Ja-j]{1}[0-9a-zA-Z]{1}', # Normal, Composite, Casual GSTIN
                r'[0-9]{4}[A-Z]{3}[0-9]{5}[UO]{1}[N][A-Z0-9]{1}', #UN/ON Body GSTIN
                r'[0-9]{4}[a-zA-Z]{3}[0-9]{5}[N][R][0-9a-zA-Z]{1}', #NRI GSTIN
                r'[0-9]{2}[a-zA-Z]{4}[a-zA-Z0-9]{1}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[DK]{1}[0-9a-zA-Z]{1}', #TDS GSTIN
                r'[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[C]{1}[0-9a-zA-Z]{1}' #TCS GSTIN
            ]
            if any(re.compile(rx).match(vat) for rx in all_gstin_re):
                return True
            raise stdnum.exceptions.InvalidComponent
        raise stdnum.exceptions.InvalidLength
