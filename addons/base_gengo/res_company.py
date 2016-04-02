# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class res_company(osv.Model):
    _name = "res.company"
    _inherit = "res.company"
    _columns = {
           "gengo_private_key": fields.text("Gengo Private Key", copy=False, groups="base.group_system"),
           "gengo_public_key": fields.text("Gengo Public Key", copy=False, groups="base.group_user"),
           "gengo_comment": fields.text("Comments", help="This comment will be automatically be enclosed in each an every request sent to Gengo", groups="base.group_user"),
           "gengo_auto_approve": fields.boolean("Auto Approve Translation ?", help="Jobs are Automatically Approved by Gengo.", groups="base.group_user"),
           "gengo_sandbox": fields.boolean("Sandbox Mode", help="Check this box if you're using the sandbox mode of Gengo, mainly used for testing purpose."),
    }

    _defaults = {
        "gengo_auto_approve": True,
    }
