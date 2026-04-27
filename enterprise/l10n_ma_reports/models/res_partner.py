from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ma_customs_vat = fields.Char(string='Customs Tax ID', help="The Customs Tax ID is needed for foreign partners in XML tax report. If left empty, customs Tax ID 20727020 will be automatically applied.")
