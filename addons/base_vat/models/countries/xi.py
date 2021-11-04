import stdnum
from odoo import models


# https://github.com/arthurdejong/python-stdnum/commit/b93d69581f35aa18e7fdd52b3f7fdf06770215e3
# Version 1.16
class VatCheck(models.AbstractModel):
    _inherit = 'base.vat.mixin'

    def check_vat_xi(self, vat):
        """ Temporary Nothern Ireland VAT validation following Brexit
        As of January 1st 2021, companies in Northern Ireland have a
        new VAT number starting with XI."""
        check_func = getattr(stdnum.util.get_cc_module('gb', 'vat'), 'validate', None)
        if not check_func:
            return len(vat) == 9
        return check_func(vat)
