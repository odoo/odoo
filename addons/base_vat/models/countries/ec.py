import stdnum
from odoo import models


# TODO this is not how it is managed in stdnum
# https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/ec/ruc.py
class VatCheck(models.AbstractModel):
    _inherit = 'base.vat.mixin'

    def is_valid_ruc_ec(self, vat):
        ci = stdnum.util.get_cc_module("ec", "ci")
        ruc = stdnum.util.get_cc_module("ec", "ruc")
        if len(vat) == 10:
            ci.validate(vat)
            return True
        elif len(vat) == 13:
            if vat[2] == "6" and ci.validate(vat[:10]):
                return True
            else:
                ruc.validate(vat)
                return True
        raise stdnum.exceptions.InvalidLength

    def check_vat_ec(self, vat):
        vat = stdnum.util.clean(vat, ' -.').upper().strip()
        return self.is_valid_ruc_ec(vat)
