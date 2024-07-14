# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    l10n_ar_computable_tax_credit = fields.Selection(related='company_id.l10n_ar_computable_tax_credit', readonly=False)
