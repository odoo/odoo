
from odoo import models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def can_edit_vat(self):
        res = super().can_edit_vat()
        if self.env.company.country_code == 'AR':
            return res or not self.vat
        return res
