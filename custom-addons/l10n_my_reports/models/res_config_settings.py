# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_my_description = fields.Html(
        related='company_id.l10n_my_description',
        string="Statement of Account report description",
        readonly=False,
    )
