# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountFiscalPositionTemplate(models.Model):

    _inherit = 'account.fiscal.position.template'

    l10n_ar_afip_responsability_type_ids = fields.Many2many(
        'l10n_ar.afip.responsability.type', 'l10n_ar_afip_reponsability_type_fiscal_pos_temp_rel',
        string='AFIP Responsability Types')
