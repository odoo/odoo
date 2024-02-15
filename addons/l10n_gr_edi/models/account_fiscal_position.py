# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    l10n_gr_edi_preferred_classification_ids = fields.One2many(
        comodel_name='l10n_gr_edi.preferred_classification',
        string='Preferred MyDATA Classification',
        inverse_name='fiscal_position_id',
    )
