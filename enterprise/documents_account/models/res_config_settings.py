# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    documents_account_settings = fields.Boolean(related='company_id.documents_account_settings', readonly=False,
                                                string="Accounting ")
    account_folder_id = fields.Many2one(related='company_id.account_folder_id', readonly=False,
                                     string="account default folder")
