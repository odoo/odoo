# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    exemption_doctor_master_account_id = fields.Many2one(
        'account.account', string="Doctors/Civil Engineers/Masters",
        related='company_id.exemption_doctor_master_account_id', readonly=False)
    exemption_bachelor_account_id = fields.Many2one(
        'account.account', string="Bachelors",
        related='company_id.exemption_bachelor_account_id', readonly=False)
    exemption_bachelor_capping_account_id = fields.Many2one(
        'account.account', string="Bachelors Capping",
        related='company_id.exemption_bachelor_capping_account_id', readonly=False)
    exemption_journal_id = fields.Many2one('account.journal', related='company_id.exemption_journal_id', readonly=False)
