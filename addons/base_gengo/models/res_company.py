# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class ResCompany(models.Model):
    _name = "res.company"
    _inherit = "res.company"

    gengo_private_key = fields.Text(copy=False,
                                    groups="base.group_system")
    gengo_public_key = fields.Text(copy=False,
                                   groups="base.group_user")
    gengo_comment = fields.Text(string="Comments",
                                help="This comment will be automatically be enclosed in each an every request sent to Gengo",
                                groups="base.group_user")
    gengo_auto_approve = fields.Boolean(string="Auto Approve Translation ?",
                                        help="Jobs are Automatically Approved by Gengo.",
                                        groups="base.group_user",
                                        default=True)
    gengo_sandbox = fields.Boolean(string="Sandbox Mode",
                                   help="Check this box if you're using the sandbox mode of Gengo, mainly used for testing purpose.")
