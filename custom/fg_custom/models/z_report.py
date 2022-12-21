# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from pytz import timezone
from odoo.exceptions import UserError

class FgZReport(models.AbstractModel):
    _name = 'report.fg_custom.report_z_pos_report'
    _description = 'Z Report'

    def action_print(self, session_id):
        session_ids = self.env['pos.session'].browse(session_id)
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
        cash_register_balance_start = 0.0
        cash_register_balance_end_real = 0.0
        tz_name = self.env.user.tz or 'UTC'
        localized_dt = timezone('UTC').localize(datetime.utcnow()).astimezone(timezone(tz_name))
        return_order_ids = self.env['pos.order']
        open_cashier_list = []
        close_cashier_list = []
        start_end_order_list = [] #trans
        receipt_start_end_order_list = [] #si
        refund_start_end_order_list = [] #refund si
        total_entry_encoding = 0

        asc_start_end_order_id = self.env['pos.order'].search([('session_id', 'in', session_ids.ids),('pos_trans_reference', '!=', False)], limit=1, order='pos_trans_reference asc')
        desc_start_end_order_id = self.env['pos.order'].search([('session_id', 'in', session_ids.ids),('pos_trans_reference', '!=', False)], limit=1, order='pos_trans_reference desc')

        asc_receipt_end_order_id = self.env['pos.order'].search([('session_id', 'in', session_ids.ids),('pos_si_trans_reference', '!=', False)], limit=1, order='pos_si_trans_reference asc')
        desc_receipt_end_order_id = self.env['pos.order'].search([('session_id', 'in', session_ids.ids),('pos_si_trans_reference', '!=', False)], limit=1, order='pos_si_trans_reference desc')

        asc_refund_end_order_id = self.env['pos.order'].search([('session_id', 'in', session_ids.ids),('pos_refund_si_reference', '!=', False)], limit=1, order='pos_refund_si_reference asc')
        desc_refund_end_order_id = self.env['pos.order'].search([('session_id', 'in', session_ids.ids),('pos_refund_si_reference', '!=', False)], limit=1, order='pos_refund_si_reference desc')

        if asc_start_end_order_id.pos_trans_reference and desc_start_end_order_id.pos_trans_reference:
            start_end_order_list.append(asc_start_end_order_id.pos_trans_reference + ' - ' + desc_start_end_order_id.pos_trans_reference)

        if asc_receipt_end_order_id.pos_si_trans_reference and desc_receipt_end_order_id.pos_si_trans_reference:
            receipt_start_end_order_list.append(asc_receipt_end_order_id.pos_si_trans_reference + ' - ' + desc_receipt_end_order_id.pos_si_trans_reference)

        if asc_refund_end_order_id.pos_refund_si_reference and desc_refund_end_order_id.pos_refund_si_reference:
            refund_start_end_order_list.append(asc_refund_end_order_id.pos_refund_si_reference + ' - ' + desc_refund_end_order_id.pos_refund_si_reference)

        for session_id in session_ids:
            return_order_ids |= session_id.order_ids.filtered(lambda x: x.pos_refund_si_reference)
            #for order in session_id.order_ids.filtered(lambda x: not x.is_refunded and x.amount_total > 0):
            for order in session_id.order_ids.filtered(lambda x: x.pos_si_trans_reference and x.amount_total > 0):
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
                else:
                    if 'Retail' in transactions_history:
                        count = transactions_history['Retail'].get('count') + 1
                        total = transactions_history['Retail'].get('total') + order.amount_total
                        transactions_history['Retail'].update({'count': count, 'total': total})
                    else:
                        transactions_history['Retail'] = {'count': 1, 'total': order.amount_total}
                if order.amount_return:
                    changes_order_count += len(order)
                    changes_order_total += order.amount_return

            for order in session_id.order_ids.filtered(lambda x: not x.is_refunded and x.amount_total > 0):
                if order.payment_ids:
                    for pay in order.payment_ids:
                        if pay.payment_method_id.name in tender_history:
                            count = tender_history[pay.payment_method_id.name].get('count') + 1
                            total = tender_history[pay.payment_method_id.name].get('total') + pay.amount
                            tender_history[pay.payment_method_id.name].update({'count': count, 'total': total})
                        else:
                            tender_history[pay.payment_method_id.name] = {'count': 1, 'total': pay.amount}

            for i in session_id.statement_ids:
                for j in i.line_ids:
                    if j.amount < 0:
                        total_entry_encoding += abs(j.amount)
                # if i.total_entry_encoding < 0:
                #     total_entry_encoding += abs(i.total_entry_encoding)
            # result_pos_pay = self.env['pos.payment'].read_group([('session_id', '=', session_id.id), ('payment_method_id.is_cash_count', '=', True)], ['amount'], ['session_id'])
            # session_amount_map = dict((data['session_id'][0], data['amount']) for data in result_pos_pay)
            # total_entry_encoding += session_amount_map.get(session_id.id) or 0
            session_start_at = timezone('UTC').localize(session_id.start_at).astimezone(timezone(tz_name))
            session_stop_at = timezone('UTC').localize(session_id.stop_at).astimezone(timezone(tz_name))
            cash_register_balance_start += session_id.cash_register_balance_start


            cash_payment_method = session_id.payment_method_ids.filtered('is_cash_count')
            total_cash_payment = 0.0
            result = self.env['pos.payment'].read_group(
                [('session_id', '=', session_id.id), ('payment_method_id', 'in', cash_payment_method.ids),
                 ('amount', '>', 0)], ['amount'], ['session_id'])
            if result:
                total_cash_payment = result[0]['amount']
            return_total_cash_payment = 0.0
            result = self.env['pos.payment'].read_group(
                [('session_id', '=', session_id.id), ('payment_method_id', 'in', cash_payment_method.ids),
                 ('amount', '<', 0)], ['amount'], ['session_id'])
            if result:
                return_total_cash_payment = result[0]['amount']
            cash_out_amount = 0
            for i in session_id.statement_ids:
                for j in i.line_ids:
                    if j.amount < 0:
                        cash_out_amount += abs(j.amount)
                # if i.total_entry_encoding < 0:
                #     cash_out_amount += abs(i.total_entry_encoding)

            # close_amount = session_id.cash_register_balance_start + total_cash_payment - abs(return_total_cash_payment) - cash_out_amount
            close_amount = session_id.cash_register_balance_start + session_id.total_payments_amount - cash_out_amount
            # cash_register_balance_end_real += session_id.cash_register_balance_end
            cash_register_balance_end_real += close_amount
            open_cashier_list.append([self.env.user.name, session_start_at.strftime('%m/%d/%Y %H:%M:%S')])
            close_cashier_list.append([self.env.user.name, session_stop_at.strftime('%m/%d/%Y %H:%M:%S')])
        data = {
                'session_id': session_ids[0] if session_ids else False,
                'open_cashier_list': open_cashier_list,
                'close_cashier_list': close_cashier_list,
                'start_end_order_list': start_end_order_list,
                'receipt_start_end_order_list': receipt_start_end_order_list,
                'refund_start_end_order_list': refund_start_end_order_list,
                'cash_register_balance_start': cash_register_balance_start,
                'cash_register_balance_end_real': cash_register_balance_end_real,
                'stop_at': localized_dt.strftime('%m/%d/%Y'), 'stop_time': localized_dt.strftime('%H:%M:%S'),
                'total_amt': total_amt,
                'total_qty': int(total_qty),
                'return_order_count': len(return_order_ids),
                'return_order_total': sum([(order.amount_total*-1) for order in return_order_ids if order]),
                'total_discount_qty': int(total_discount_qty),
                'total_discount_percentage': total_discount_percentage,
                'total_discount_global_minus': total_discount_global_minus,
                'total_discount_coupon_minus': total_discount_coupon_minus,
                'total_vat': total_vat,
                'total_vat_qty': int(total_vat_qty),
                'total_product_v': total_product_v,
                'total_product_e': total_product_e,
                'total_product_z': total_product_z,
                'total_entry_encoding': total_entry_encoding,
                'transactions_history': transactions_history,
                'tender_history': tender_history,
                'changes_order_count': int(changes_order_count),
                'changes_order_total': changes_order_total,
                }
        return data

    @api.model
    def _get_report_values(self, docids, data=None):
        if docids:
            return self.action_print(docids)
        if data and data.get('session_id', False):
            return self.action_print(data.get('session_id'))
        else:
            raise UserError(_("Form content is missing, this report cannot be printed."))