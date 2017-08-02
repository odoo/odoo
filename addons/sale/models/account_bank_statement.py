# -*- coding: utf-8 -*-

from odoo import api, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.multi
    def get_data_for_reconciliation_widget(self, excluded_ids=None):
        lines = super(AccountBankStatementLine, self).get_data_for_reconciliation_widget(excluded_ids=excluded_ids)
        for line in lines:
            line['order_ids'] = self.get_available_saleorder_for_reconciliation(line['st_line']['currency_id'], line['st_line']['partner_id'])
        return lines

    def get_available_saleorder_for_reconciliation(self, currency_id, partner_id=None):
        """
        Changes use to toggle the sale orders reconciliation button (risk of decreasing the display speed of the reconciliation widget)
        """
        domain = [("state", "in", ["sent", "sale"]), ("invoice_status", "!=", "invoiced"), ('currency_id', '=', currency_id)]
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        return self.env['sale.order'].search(domain).ids


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def get_data_for_manual_reconciliation(self, res_type, res_ids=None, account_type=None):
        """
        Changes use to toggle the sale orders reconciliation button (risk of decreasing the display speed of the reconciliation widget)
        """
        lines = super(AccountMoveLine, self).get_data_for_manual_reconciliation(res_type=res_type, res_ids=res_ids, account_type=account_type)
        Statement = self.env['account.bank.statement.line']
        for line in lines:
            line['order_ids'] = Statement.get_available_saleorder_for_reconciliation(line['currency_id'], line['partner_id'])
        return lines
