import stdnum
from odoo import models


# TODO vat not declared in UA in stdnum
# https://github.com/odoo/odoo/commit/0783530e145c6bc7e83b4a3730bd7a0480c2dd59
class VatCheck(models.AbstractModel):
    _inherit = 'base.vat.mixin'

    def check_vat_ua(self, vat):
        if self.commercial_partner_id.country_id.code == 'MX':
            if len(vat) == 10:
                return True
            else:
                raise stdnum.exceptions.InvalidLength
        elif self.commercial_partner_id.is_company:
            if len(vat) == 12:
                return True
            else:
                raise stdnum.exceptions.InvalidLength
        else:
            if len(vat) == 10 or len(vat) == 9:
                return True
            else:
                raise stdnum.exceptions.InvalidLength
