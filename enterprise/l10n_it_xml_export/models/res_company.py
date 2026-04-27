from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_countries_allowing_tax_representative(self):
        rslt = super()._get_countries_allowing_tax_representative()
        rslt.add('IT')
        return rslt
