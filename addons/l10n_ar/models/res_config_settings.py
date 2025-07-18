# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ar_afip_activity_ids = fields.Many2many(
        'afip.activity', 'activities_company_rel', string='AFIP Activities',
        help="Activities of the company according to AFIP. This field is used to set the activities for the company in the configuration settings.",
        related='company_id.l10n_ar_activity_ids', readonly=False)
