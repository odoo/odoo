from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_tr_nilvera_edispatch_customs_zip = fields.Char(
        string="Customs ZIP",
        related='partner_id.l10n_tr_nilvera_edispatch_customs_zip',
        readonly=False
    )
