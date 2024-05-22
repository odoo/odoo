# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountFiscalPositionTemplate(models.Model):

    _inherit = 'account.fiscal.position.template'

    l10n_ar_afip_responsibility_type_ids = fields.Many2many(
        'l10n_ar.afip.responsibility.type', 'l10n_ar_afip_reponsibility_type_fiscal_pos_temp_rel',
        string='AFIP Responsibility Types')
