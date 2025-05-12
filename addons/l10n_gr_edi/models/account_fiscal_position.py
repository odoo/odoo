from odoo import fields, models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    l10n_gr_edi_preferred_classification_ids = fields.One2many(
        comodel_name='l10n_gr_edi.preferred_classification',
        string='Preferred myDATA Classification',
        inverse_name='fiscal_position_id',
    )
