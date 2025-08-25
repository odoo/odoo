# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ar_state_id = fields.Many2one(
        'res.country.state', string="Jurisdiction", ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    l10n_ar_tribute_afip_code = fields.Selection(related='tax_group_id.l10n_ar_tribute_afip_code')
