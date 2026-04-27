# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class AccountTaxReportActivity(models.Model):
    _inherit = "mail.activity"

    account_tax_closing_params = fields.Json(string="Tax closing additional params")

    def action_open_tax_activity(self):
        self.ensure_one()
        if self.activity_type_id == self.env.ref('account_reports.mail_activity_type_tax_report_to_pay'):
            move = self.env['account.move'].browse(self.res_id)
            return move._action_tax_to_pay_wizard()
        elif self.activity_type_id == self.env.ref('account_reports.mail_activity_type_tax_report_to_be_sent'):
            move = self.env['account.move'].browse(self.res_id)
            return move._action_tax_to_send()

        if self.activity_type_id == self.env.ref('account_reports.mail_activity_type_tax_report_error'):
            move = self.env['account.move'].browse(self.res_id)
            return move._action_tax_report_error()

        journal = self.env['account.journal'].browse(self.res_id)
        options = {}
        if self.account_tax_closing_params:
            options = self.env['account.move']._get_tax_closing_report_options(
                journal.company_id,
                self.env['account.fiscal.position'].browse(self.account_tax_closing_params['fpos_id']) if self.account_tax_closing_params['fpos_id'] else False,
                self.env['account.report'].browse(self.account_tax_closing_params['report_id']),
                fields.Date.from_string(self.account_tax_closing_params['tax_closing_end_date'])
            )
        action = self.env["ir.actions.actions"]._for_xml_id("account_reports.action_account_report_gt")
        action.update({'params': {'options': options, 'ignore_session': True}})
        return action
