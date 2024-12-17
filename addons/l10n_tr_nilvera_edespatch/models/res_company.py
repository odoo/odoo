from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_tr_nilvera_edespatch_customs_zip = fields.Char(
        related='partner_id.l10n_tr_nilvera_edespatch_customs_zip',
        readonly=False
    )
    country_code = fields.Char(related='country_id.code')
