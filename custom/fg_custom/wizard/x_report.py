# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
import datetime


class XReport(models.TransientModel):
    _name = "x.report"
    _description = "X Report"

    session_id = fields.Many2one('pos.session', 'Session')
    
    def action_print(self):
        session_id = self.session_id
        start_order_id = self.env['pos.order'].search([('session_id', '=', session_id.id)], limit=1, order='id asc')
        end_order_id = self.env['pos.order'].search([('session_id', '=', session_id.id)], limit=1, order='id desc')
        return_order_ids = session_id.order_ids.filtered(lambda x: x.is_refunded)
        discount_order_ids = []
        tax_order_count = 0
        tax_order_total = 0.0
        vatable_order = 0.0
        non_vatable_order = 0.0
        zero_vatable_order = 0.0
        count = 0
        total = 0.0
        transactions_history = {}
        tender_history = {}
        changes_order_count = 0.0
        changes_order_total = 0.0
        for order in session_id.order_ids:
            discount_order_ids.append(order.lines.filtered(lambda x: x.discount > 0.0))
            tax_order_count += order.amount_tax and len(order)
            tax_order_total += order.amount_tax
            if order.amount_return:
                changes_order_count += len(order)
                changes_order_total += order.amount_return
            for line in order.lines:
                if line.tax_ids_after_fiscal_position:
                    for tax in line.tax_ids_after_fiscal_position:
                        if tax.is_non_zero_vat == 'is_vat':
                            vatable_order += order.amount_total
                        if tax.is_non_zero_vat == 'is_non_vat':
                            non_vatable_order += order.amount_total
                        if tax.is_non_zero_vat == 'is_zero_vat':
                            zero_vatable_order += order.amount_total
            if order.x_ext_source:
                if order.x_ext_source in transactions_history:
                    count = transactions_history[order.x_ext_source].get('count') and transactions_history[order.x_ext_source].get('count') + len(order)
                    total = transactions_history[order.x_ext_source].get('total') and transactions_history[order.x_ext_source].get('total') + order.amount_total
                    transactions_history[order.x_ext_source].update({'count': count, 'total': float(format(total, '.2f'))})
                else:
                    transactions_history[order.x_ext_source] = {'count': len(order), 'total': float(format(order.amount_total, '.2f'))}
            if order.payment_ids:
                for pay in order.payment_ids:
                    if pay.payment_method_id.name in tender_history:
                        count = tender_history[pay.payment_method_id.name].get('count') and tender_history[pay.payment_method_id.name].get('count') + len(order)
                        total = tender_history[pay.payment_method_id.name].get('total') and tender_history[pay.payment_method_id.name].get('total') + order.amount_total
                        tender_history[pay.payment_method_id.name].update({'count': count, 'total': float(format(total, '.2f'))})
                    else:
                        tender_history[pay.payment_method_id.name] = {'count': len(order), 'total': float(format(order.amount_total, '.2f'))}
            
        data = {'session_id': session_id, 'session_name': session_id.name,
                'start_at': session_id.start_at, 'start_order_id': start_order_id.name,
                'end_order_id': end_order_id.name, 'cash_register_balance_start': session_id.cash_register_balance_start,
                'cash_register_balance_end_real': session_id.cash_register_balance_end_real,
                'total_payments_amount': session_id.total_payments_amount, 'order_count': session_id.order_count,
                'return_order_count': len(return_order_ids), 'return_order_total': sum([order.amount_total for order in return_order_ids if order]),
                'discount_order_count': len([line.order_id for line in discount_order_ids if line]),
                'discount_order_total': sum([line.discount for line in discount_order_ids if line.discount > 0.0]),
                'tax_order_count': tax_order_count, 'tax_order_total': float(format(tax_order_total, '.2f')),
                'vatable_order': float(format(vatable_order, '.2f')), 'zero_vatable_order': float(format(zero_vatable_order, '.2f')), 'non_vatable_order': float(format(non_vatable_order, '.2f')),
                'transactions_history': transactions_history,'tender_history': tender_history,
                'changes_order_count': changes_order_count, 'changes_order_total': float(format(changes_order_total, '.2f')),
                'stop_at': datetime.datetime.now().date(), 'stop_time': datetime.datetime.now().time(),
                }
        return self.env.ref('fg_custom.x_pos_report').report_action(self, data=data)