# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import pytz
from datetime import datetime, date, timedelta
from pytz import timezone, UTC
from dateutil.relativedelta import relativedelta

class XReport(models.TransientModel):
    _name = "x.report"
    _description = "X Report"

    user_id = fields.Many2one('res.users', string='Cashier User (Opened By)', required=True, default=lambda self: self.env.uid)
    start_at = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    session_id = fields.Many2one('pos.session', domain="[('state', '=', 'opened'), ('user_id', '=', user_id)]", string='Session', required=True)

    @api.onchange('start_at', 'user_id')
    def onchange_start_at(self):
        if self.start_at:
            # 00: 00:00
            date_start = fields.Datetime.to_string(self.start_at)
            # 23: 59:59
            date_stop = fields.Datetime.to_string(self.start_at + relativedelta(hours=23, minutes=59, seconds=59))
            return {'domain': {'session_id': [('start_at', '>=', date_start), ('start_at', '<=', date_stop), ('state', '=', 'opened'), ('user_id', '=', self.user_id.id)]}}

    def action_print(self):
        data = {'session_id': self.session_id.id}
        return self.env.ref('fg_custom.x_pos_report').report_action(None, data=data)

    def action_print_old(self):
        session_id = self.session_id
        start_order_id = self.env['pos.order'].search([('session_id', '=', session_id.id)], limit=1, order='pos_si_trans_reference asc')
        end_order_id = self.env['pos.order'].search([('session_id', '=', session_id.id)], limit=1, order='pos_si_trans_reference desc')
        return_order_ids = session_id.order_ids.filtered(lambda x: x.is_refunded)
        # discount_line = []
        # discount_reward_line = []
        # tax_order_count = 0
        # tax_order_total = 0.0
        # vatable_order = 0.0
        # non_vatable_order = 0.0
        # zero_vatable_order = 0.0
        # count = 0
        # total = 0.0
        # transactions_history = {}
        # tender_history = {}
        # changes_order_count = 0.0
        # changes_order_total = 0.0
        total_qty = 0
        total_discount_qty = 0
        total_vat = 0
        total_vat_qty = 0
        total_amt = 0

        total_discount_percentage = 0
        total_discount_global_minus = 0
        total_discount_coupon_minus = 0

        total_product_v = 0
        total_product_e = 0
        total_product_z = 0

        transactions_history = {}
        tender_history = {}

        changes_order_count = 0.0
        changes_order_total = 0.0
        for order in session_id.order_ids.filtered(lambda x: not x.is_refunded and x.amount_total > 0):
            total_qty += 1
            is_total_discount_qty = False
            is_total_vat_qty = False
            for line in order.lines:
                if line.discount > 0:
                    is_total_discount_qty = True
                    total_discount_percentage += (line.price_unit * line.qty) - line.price_subtotal_incl
                if line.price_unit >= 0 and not line.is_program_reward:
                    current_total_vat = line.price_subtotal_incl - line.price_subtotal
                    total_vat += current_total_vat
                    if current_total_vat > 0:
                        is_total_vat_qty = True
                    total_amt += line.price_unit * line.qty
                    str_non_zero_vat = ''
                    for i in line.tax_ids_after_fiscal_position:
                        str_non_zero_vat = i.is_non_zero_vat
                    if str_non_zero_vat == 'is_vat':
                        total_product_v += line.price_subtotal
                    elif str_non_zero_vat == 'is_zero_vat':
                        total_product_z += line.price_subtotal
                    else:
                        total_product_e += line.price_subtotal
                else:
                    is_total_discount_qty = True
                    # is_total_vat_qty = True
                    total_vat += line.price_subtotal_incl - line.price_subtotal
                    str_non_zero_vat = ''
                    for i in line.tax_ids_after_fiscal_position:
                        str_non_zero_vat = i.is_non_zero_vat
                    if str_non_zero_vat == 'is_vat':
                        total_product_v += line.price_subtotal
                    if line.is_program_reward:
                        total_discount_coupon_minus += abs(line.price_unit)
                    else:
                        total_discount_global_minus += abs(line.price_unit)
            if is_total_discount_qty:
                total_discount_qty += 1
            if is_total_vat_qty:
                total_vat_qty += 1

            if order.x_ext_source:
                if order.x_ext_source in transactions_history:
                    count = transactions_history[order.x_ext_source].get('count') + 1
                    total = transactions_history[order.x_ext_source].get('total') + order.amount_total
                    transactions_history[order.x_ext_source].update({'count': count, 'total': total})
                else:
                    transactions_history[order.x_ext_source] = {'count': 1, 'total': order.amount_total}

            if order.payment_ids:
                for pay in order.payment_ids:
                    if pay.payment_method_id.name in tender_history:
                        count = tender_history[pay.payment_method_id.name].get('count') + 1
                        total = tender_history[pay.payment_method_id.name].get('total') + pay.amount
                        tender_history[pay.payment_method_id.name].update({'count': count, 'total': total})
                    else:
                        tender_history[pay.payment_method_id.name] = {'count': 1, 'total': pay.amount}

            if order.amount_return:
                changes_order_count += len(order)
                changes_order_total += order.amount_return

            # discount_line.append(order.lines.filtered(lambda x: x.discount > 0.0))
            # discount_reward_line.append(order.lines.filtered(lambda x: x.is_program_reward))
            # tax_order_count += order.amount_tax and len(order)
            # tax_order_total += order.amount_tax
            # if order.amount_return:
            #     changes_order_count += len(order)
            #     changes_order_total += order.amount_return
            # for line in order.lines:
            #     if line.tax_ids_after_fiscal_position:
            #         for tax in line.tax_ids_after_fiscal_position:
            #             if tax.is_non_zero_vat == 'is_vat':
            #                 vatable_order += order.amount_total
            #             if tax.is_non_zero_vat == 'is_non_vat':
            #                 non_vatable_order += order.amount_total
            #             if tax.is_non_zero_vat == 'is_zero_vat':
            #                 zero_vatable_order += order.amount_total
            # if order.x_ext_source:
            #     if order.x_ext_source in transactions_history:
            #         count = transactions_history[order.x_ext_source].get('count') and transactions_history[order.x_ext_source].get('count') + len(order)
            #         total = transactions_history[order.x_ext_source].get('total') and transactions_history[order.x_ext_source].get('total') + order.amount_total
            #         transactions_history[order.x_ext_source].update({'count': count, 'total': float(format(total, '.2f'))})
            #     else:
            #         transactions_history[order.x_ext_source] = {'count': len(order), 'total': float(format(order.amount_total, '.2f'))}
            # if order.payment_ids:
            #     for pay in order.payment_ids:
            #         if pay.payment_method_id.name in tender_history:
            #             count = tender_history[pay.payment_method_id.name].get('count') and tender_history[pay.payment_method_id.name].get('count') + len(order)
            #             total = tender_history[pay.payment_method_id.name].get('total') and tender_history[pay.payment_method_id.name].get('total') + pay.amount
            #             tender_history[pay.payment_method_id.name].update({'count': count, 'total': float(format(total, '.2f'))})
            #         else:
            #             tender_history[pay.payment_method_id.name] = {'count': len(order), 'total': float(format(pay.amount, '.2f'))}
        tz_name = self.env.user.tz or 'UTC'
        localized_dt = timezone('UTC').localize(datetime.utcnow()).astimezone(timezone(tz_name))
        session_start_at = timezone('UTC').localize(session_id.start_at).astimezone(timezone(tz_name))
        print('-----localized_dt, session_start_at---', localized_dt, session_start_at)
        data = {'session_name': session_id.name, 'start_at': session_start_at,
                 'start_order_id': start_order_id.pos_si_trans_reference, 'end_order_id': end_order_id.pos_si_trans_reference, 'cash_register_balance_start': session_id.cash_register_balance_start,
                 'cash_register_balance_end_real': session_id.cash_register_balance_end_real, 'stop_at': localized_dt.strftime('%m/%d/%Y'), 'stop_time': localized_dt.strftime('%H:%M:%S'),
                 'total_amt': total_amt,
                 'total_qty': int(total_qty),
                 'return_order_count': len(return_order_ids),
                 'return_order_total': sum([order.amount_total for order in return_order_ids if order]),
                 'total_discount_qty': int(total_discount_qty),
                 'total_discount_percentage': total_discount_percentage,
                 'total_discount_global_minus': total_discount_global_minus,
                 'total_discount_coupon_minus': total_discount_coupon_minus,
                 'total_vat': total_vat,
                 'total_vat_qty': int(total_vat_qty),
                 'total_product_v': total_product_v,
                 'total_product_e': total_product_e,
                 'total_product_z': total_product_z,
                 'transactions_history': transactions_history,
                 'tender_history': tender_history,
                 'changes_order_count': int(changes_order_count),
                 'changes_order_total': changes_order_total,
                 }
        print('------data----', data)
        # data = {'session_id': session_id, 'session_name': session_id.name,
        #         'start_at': session_start_at,
        #         'start_order_id': start_order_id.name,
        #         'end_order_id': end_order_id.name, 'cash_register_balance_start': session_id.cash_register_balance_start,
        #         'cash_register_balance_end_real': session_id.cash_register_balance_end_real,
        #         'total_payments_amount': session_id.total_payments_amount, 'order_count': session_id.order_count,
        #         'return_order_count': len(return_order_ids), 'return_order_total': sum([order.amount_total for order in return_order_ids if order]),
        #         'discount_order_count': len([line.order_id for line in [] if line]),
        #         'discount_order_total': discount_order_total,
        #         'tax_order_count': tax_order_count, 'tax_order_total': float(format(tax_order_total, '.2f')),
        #         'vatable_order': float(format(vatable_order, '.2f')), 'zero_vatable_order': float(format(zero_vatable_order, '.2f')), 'non_vatable_order': float(format(non_vatable_order, '.2f')),
        #         'transactions_history': transactions_history,'tender_history': tender_history,
        #         'changes_order_count': changes_order_count, 'changes_order_total': float(format(changes_order_total, '.2f')),
        #         'stop_at': localized_dt.strftime('%m/%d/%Y'), 'stop_time': localized_dt.strftime('%H:%M:%S'),
        #         }
        return self.env.ref('fg_custom.x_pos_report').report_action(self, data=data)
