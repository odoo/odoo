# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_au_branch_code = fields.Char(
        related="company_id.l10n_au_branch_code", readonly=False)
    l10n_au_wpn_number = fields.Char(
        related="company_id.l10n_au_wpn_number", readonly=False)
    l10n_au_registered_for_whm = fields.Boolean(related="company_id.l10n_au_registered_for_whm", readonly=False)
    l10n_au_registered_for_palm = fields.Boolean(related="company_id.l10n_au_registered_for_palm", readonly=False)
