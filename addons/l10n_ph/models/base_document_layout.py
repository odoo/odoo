# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    account_fiscal_country_id = fields.Many2one(related='company_id.account_fiscal_country_id')
    l10n_ph_is_vat_registered = fields.Boolean(related='company_id.l10n_ph_is_vat_registered')
