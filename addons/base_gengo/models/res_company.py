# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class res_company(models.Model):
    _inherit = "res.company"

    gengo_private_key = fields.Text(string="Gengo Private Key", copy=False, groups="base.group_system")
    gengo_public_key = fields.Text(string="Gengo Public Key", copy=False, groups="base.group_user")
    gengo_comment = fields.Text(string="Comments", groups="base.group_user",
      help="This comment will be automatically be enclosed in each an every request sent to Gengo")
    gengo_auto_approve = fields.Boolean(string="Auto Approve Translation ?", groups="base.group_user", default=True,
      help="Jobs are Automatically Approved by Gengo.")
    gengo_sandbox = fields.Boolean(string="Sandbox Mode",
      help="Check this box if you're using the sandbox mode of Gengo, mainly used for testing purpose.")
