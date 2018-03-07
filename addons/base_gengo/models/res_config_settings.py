# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gengo_private_key = fields.Text(string="Gengo Private Key", related="company_id.gengo_private_key",
      related_sudo=False)
    gengo_public_key = fields.Text(string="Gengo Public Key", related="company_id.gengo_public_key",
      related_sudo=False)
    gengo_comment = fields.Text(string="Comments", related="company_id.gengo_comment",
      related_sudo=False,
      help="This comment will be automatically be enclosed in each an every request sent to Gengo")
    gengo_auto_approve = fields.Boolean(string="Auto Approve Translation ?",
      related="company_id.gengo_auto_approve", related_sudo=False,
      help="Jobs are Automatically Approved by Gengo.")
    gengo_sandbox = fields.Boolean(string="Sandbox Mode",
      help="Check this box if you're using the sandbox mode of Gengo, mainly used for testing purpose.")
