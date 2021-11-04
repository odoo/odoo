import stdnum
from odoo import models
from . import check_stdnum_version


# https://github.com/arthurdejong/python-stdnum/commit/fcbe159119e105af796674f4a2ddd37489031ccb
check_stdnum_version('1.14')
class VatCheck(models.AbstractModel):
    _inherit = 'base.vat.mixin'

    def check_vat_pe(self, vat):
        return stdnum.util.get_cc_module('pe', 'ruc').validate(vat)
