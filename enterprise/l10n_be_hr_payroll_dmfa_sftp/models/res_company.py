# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    onss_technical_user_name = fields.Char(string="ONSS Technical User Name", groups="base.group_system",
        help="ONSS Technical User Name provided when registering service on the ONSS platform")
    onss_sftp_private_key = fields.Many2one('certificate.key', string="ONSS Technical User Private Key", groups="base.group_system")
