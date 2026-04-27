# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    onss_technical_user_name = fields.Char(
        related="company_id.onss_technical_user_name",
        readonly=False,
        groups="hr_payroll.group_hr_payroll_user")
    onss_sftp_private_key = fields.Many2one(
        related="company_id.onss_sftp_private_key",
        readonly=False,
        groups="hr_payroll.group_hr_payroll_user")
