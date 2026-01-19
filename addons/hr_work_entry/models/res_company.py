# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    external_code = fields.Char("External Code", groups="hr.group_hr_user", copy=False, help="Use this code to export your data to a third party")
