# -*- coding: utf-8 -*-

from odoo import api, models


class Reconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation'

    @api.model
    def get_data_for_reconciliation_widget(self, statement_line_ids, excluded_ids=None):
        lines = super(Reconciliation, self).get_data_for_reconciliation_widget(statement_line_ids=statement_line_ids, excluded_ids=excluded_ids)
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

    @api.model
    def get_data_for_manual_reconciliation(self, res_type, res_ids=None, account_type=None):
        """
        Changes use to toggle the sale orders reconciliation button (risk of decreasing the display speed of the reconciliation widget)
        """
        lines = super(Reconciliation, self).get_data_for_manual_reconciliation(res_type=res_type, res_ids=res_ids, account_type=account_type)
        Statement = self.env['account.bank.statement.line']
        for line in lines:
            line['order_ids'] = self.get_available_saleorder_for_reconciliation(line['currency_id'], line['partner_id'])
        return lines

    @api.model
    def reconciliation_create_move_lines_propositions(self, order_ids, invoice_ids, target_currency):
        sale_orders = self.env['sale.order'].browse(order_ids)
        self.env['account.invoice'].browse(invoice_ids).action_invoice_open()
        move_lines = self.get_move_lines_for_reconciliation(additional_domain=[('invoice_id', 'in', invoice_ids)])
        return self.prepare_move_lines_for_reconciliation_widget(move_lines, target_currency=target_currency)
