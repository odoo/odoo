import stdnum
from odoo import models
from . import check_stdnum_version


# https://github.com/arthurdejong/python-stdnum/commit/cc3a970e893ebe6635982bcd49c48e6549cb5ac3
check_stdnum_version('1.15')
class VatCheck(models.AbstractModel):
    _inherit = 'base.vat.mixin'

    def check_vat_au(self, vat):
        '''
        The Australian equivalent of a VAT number is an ABN number.
        TFN (Australia Tax file numbers) are private and not to be
        entered into systems or publicly displayed, so ABN numbers
        are the public facing number that legally must be displayed
        on all invoices
        '''
        check_func = getattr(stdnum.util.get_cc_module('au', 'abn'), 'validate', None)
        if not check_func:
            vat = vat.replace(" ", "")
            return len(vat) == 11 and vat.isdigit()
        return check_func(vat)
