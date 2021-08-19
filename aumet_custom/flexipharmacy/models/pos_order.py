# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
import psycopg2
import pytz
from odoo import models, fields, api, tools, _
from odoo.tools import float_is_zero, float_round
from datetime import timedelta, datetime, timezone, date
from dateutil.tz import tzutc, tzlocal
import logging
from odoo.exceptions import UserError
from odoo.osv.expression import AND

_logger = logging.getLogger(__name__)


def start_end_date_global(start, end, tz):
    tz = pytz.timezone(tz) or 'UTC'
    current_time = datetime.now(tz)
    hour_tz = int(str(current_time)[-5:][:2])
    min_tz = int(str(current_time)[-5:][3:])
    sign = str(current_time)[-6][:1]
    sdate = start + " 00:00:00"
    edate = end + " 23:59:59"
    if sign == '-':
        start_date = (datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
        end_date = (datetime.strptime(edate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                              minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
    if sign == '+':
        start_date = (datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
        end_date = (datetime.strptime(edate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                              minutes=min_tz)).strftime(
            "%Y-%m-%d %H:%M:%S")
    return start_date, end_date


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.depends('amount_total', 'amount_paid')
    def _compute_amount_due(self):
        for each in self:
            each.amount_due = (each.amount_total - each.amount_paid) + each.change_amount_for_wallet

    def _commission_calculation(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'flexipharmacy.pos_commission_calculation') or ''

    def commission_based(self):
        return self.env['ir.config_parameter'].sudo().get_param('flexipharmacy.pos_commission_based_on') or ''

    # store wallet amount
    change_amount_for_wallet = fields.Float('Wallet Amount')
    amount_due = fields.Float("Amount Due", compute="_compute_amount_due")
    sales_person_id = fields.Many2one('res.users', string='Order User')
    earned_points = fields.Integer('Earned Points', readonly="1")
    redeem_points = fields.Integer('Redeem Points', readonly="1")
    points_amount = fields.Integer('Points Amount', readonly="1")
    ref_reward = fields.Integer('Reference Points', readonly="1")
    ref_customer = fields.Integer('Reference Customer', readonly="1")
    back_order_reference = fields.Char('Back Order Receipt', readonly="1")
    salesman_id = fields.Many2one('res.users', string='Salesman')
    is_recurrent = fields.Boolean(string='Recurrent')
    is_delivery_recurrent = fields.Boolean(string='Delivery Recurrent')

    is_delivery_charge = fields.Boolean(string="Is Delivery Charge")
    delivery_user_id = fields.Many2one("res.users", string="Delivery User")
    delivery_date = fields.Datetime("Delivery Date")
    delivery_address = fields.Char("Delivery Address")
    delivery_charge_amt = fields.Float("Delivery Charge")
    delivery_type = fields.Selection([
        ('none', 'None'),
        ('pending', 'Pending'),
        ('delivered', 'Delivered')],
        string="Delivery Type", default="none")

    signature = fields.Binary(string="Signature")
    rating = fields.Selection(
        [('0', 'No Ratings'), ('1', 'Bad'), ('2', 'Not bad'), ('3', 'Good'), ('4', 'Very Good'), ('5', 'Excellent')],
        'Rating', default='0', index=True)
    ref_doctor_id = fields.Many2one('res.partner', string='Reference Doctor', readonly="1")
    pos_return_order = fields.Integer(compute='_compute_pos_return_order_count')
    remaining_lines = fields.One2many('pos.order.line', 'order_id', string='Remaining Order Lines',
                                      states={'draft': [('readonly', False)]}, readonly=True, copy=True)
    sale_commission_ids = fields.One2many('pos.order.commission', 'pos_order_id', string="Doctor Commission")
    commission_calculation = fields.Selection([
        ('product', 'Product'),
        ('product_category', 'Product Category'),
        ('doctor', 'Doctor'),
    ], string='Commission Calculation', default=_commission_calculation, readonly=1, store=True)
    commission_based_on = fields.Selection([
        ('product_sell_price', 'Product Sell Price'),
        ('product_profit_margin', 'Product Profit Margin'),
    ], string='Commission Based On', default=commission_based, readonly=1, store=True)

    def _compute_pos_return_order_count(self):
        for order in self:
            order_id_count = self.search_count([('back_order_reference', '=', order.pos_reference)])
            order.pos_return_order = order_id_count

    def action_pos_return_order(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('point_of_sale.action_pos_pos_form')
        action['context'] = {}
        action['domain'] = [('back_order_reference', '=', self.pos_reference)]
        return action

    def check_order_delivery_type(self):
        if self.delivery_type == 'pending' and self.state == 'draft':
            action_id = self.env.ref('point_of_sale.action_pos_payment')
            return {
                'name': _(action_id.name),
                'type': action_id.type,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': action_id.res_model,
                'target': 'new',
                'context': {'from_delivery': True},
            }

        elif self.delivery_type == 'pending' and self.state == 'paid':
            self.write({'delivery_type': 'delivered'})
            self.picking_ids._action_done()
            return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _export_for_ui(self, order):
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        return {
            'lines': [[0, 0, line] for line in order.lines.export_for_ui()],
            'statement_ids': [[0, 0, payment] for payment in order.payment_ids.export_for_ui()],
            'name': order.pos_reference,
            'uid': order.pos_reference[6:],
            'amount_paid': order.amount_paid,
            'amount_total': order.amount_total,
            'amount_tax': order.amount_tax,
            'amount_return': order.amount_return,
            'pos_session_id': order.session_id.id,
            'is_session_closed': order.session_id.state == 'closed',
            'pricelist_id': order.pricelist_id.id,
            'partner_id': order.partner_id.id,
            'user_id': order.user_id.id,
            'sequence_number': order.sequence_number,
            'creation_date': order.date_order.astimezone(timezone),
            'fiscal_position_id': order.fiscal_position_id.id,
            'to_invoice': order.to_invoice,
            'state': order.state,
            'account_move': order.account_move.id,
            'id': order.id,
            'is_tipped': order.is_tipped,
            'order_note': order.note,
            'tip_amount': order.tip_amount,
        }

    @api.model
    def _process_order(self, order, draft, existing_order):
        """Create or update an pos.order from a given dictionary.
        :param dict order: dictionary representing the order.
        :param bool draft: Indicate that the pos_order is not validated yet.
        :param existing_order: order to be updated or False.
        :type existing_order: pos.order.
        :returns: id of created/updated pos.order
        :rtype: int
        """
        order = order['data']
        pos_session = self.env['pos.session'].browse(order['pos_session_id'])
        if pos_session.state == 'closing_control' or pos_session.state == 'closed':
            order['pos_session_id'] = self._get_valid_session(order).id

        pos_order = False
        if not existing_order:
            pos_order = self.create(self._order_fields(order))
        else:
            pos_order = existing_order
            pos_order.lines.unlink()
            order['user_id'] = pos_order.user_id.id
            pos_order.write(self._order_fields(order))

        pos_order = pos_order.with_company(pos_order.company_id)
        self = self.with_company(pos_order.company_id)
        self._process_payment_lines(order, pos_order, pos_session, draft)

        if not draft:
            try:
                pos_order.action_pos_order_paid()
            except psycopg2.DatabaseError:
                # do not hide transactional errors, the order(s) won't be saved!
                raise
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))
        if order['get_delivery_charge_data'] and order['get_delivery_charge']:
            get_delivery_data = order.get('get_delivery_charge_data')
            get_delivery_charge = order.get('get_delivery_charge_data')
            time = '00:00'
            if get_delivery_data.get('DeliveryTime'):
                time = get_delivery_data.get('DeliveryTime')
            delivery_datetime_str = get_delivery_data.get('DeliveryDate') + " " + time + ":00"
            local = pytz.timezone(self.env.user.tz)
            delivery_datetime = datetime.strptime(delivery_datetime_str, "%Y-%m-%d %H:%M:%S")
            local_dt = local.localize(delivery_datetime, is_dst=None)
            utc_dt = local_dt.astimezone(pytz.utc)
            dt_string = str(utc_dt)
            new_dt = dt_string[:19]
            utc_delivery_datetime = datetime.strptime(new_dt, '%Y-%m-%d %H:%M:%S')
            vals = {
                'is_delivery_charge': get_delivery_data.get('IsDeliveryCharge'),
                'delivery_user_id': int(get_delivery_data.get('DeliveryUser')),
                'delivery_date': utc_delivery_datetime,
                'delivery_address': get_delivery_data.get('CustomerAddress'),
                'delivery_charge_amt': get_delivery_charge.get('amount'),
                'delivery_type': 'pending',
            }
            pos_order.write(vals)
        pos_order._create_order_picking()
        if pos_order.to_invoice and pos_order.state == 'paid':
            pos_order.action_pos_order_invoice()

        if pos_order:
            if order['wallet_type']:
                self.wallet_management(order, pos_order)
            if order.get('giftcard') or order.get('redeem') or order.get('recharge'):
                self.gift_card_management(order, pos_order)
            if order.get('voucher_redeem'):
                self.gift_voucher_management(order)
            if order.get('partner_id') and pos_order:
                self.loyalty_management(order, pos_order)
        return pos_order.id

    def _create_order_picking(self):
        self.ensure_one()
        if self.is_delivery_charge:
            picking_type = self.config_id.picking_type_id
            if self.partner_id.property_stock_customer:
                destination_id = self.partner_id.property_stock_customer.id
            elif not picking_type or not picking_type.default_location_dest_id:
                destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
            else:
                destination_id = picking_type.default_location_dest_id.id

            pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(destination_id, self.lines,
                                                                                      picking_type, self.partner_id,
                                                                                      self.is_delivery_charge)
            pickings.write({'pos_session_id': self.session_id.id, 'pos_order_id': self.id, 'origin': self.name})

        if (not self.is_delivery_charge and not self.session_id.update_stock_at_closing) or (
                self.company_id.anglo_saxon_accounting and self.to_invoice and not self.is_delivery_charge):
            picking_type = self.config_id.picking_type_id
            if self.partner_id.property_stock_customer:
                destination_id = self.partner_id.property_stock_customer.id
            elif not picking_type or not picking_type.default_location_dest_id:
                destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
            else:
                destination_id = picking_type.default_location_dest_id.id

            pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(destination_id, self.lines,
                                                                                      picking_type, self.partner_id)
            pickings.write({'pos_session_id': self.session_id.id, 'pos_order_id': self.id, 'origin': self.name})

    def action_pos_order_paid(self):
        self.ensure_one()
        if self.config_id.enable_wallet:
            if not self.config_id.cash_rounding:
                total = self.amount_total
            else:
                total = float_round(0, precision_rounding=self.config_id.rounding_method.rounding,
                                    rounding_method=self.config_id.rounding_method.rounding_method)
            if not float_is_zero(0, precision_rounding=self.currency_id.rounding):
                raise UserError(_("Order %s is not fully paid.", self.name))

            self.write({'state': 'paid'})
        return super(PosOrder, self).action_pos_order_paid()

    def loyalty_management(self, data, pos_order_id):
        loyalty_vals = {
            'order_no': pos_order_id.name,
            'order_date': datetime.now(),
            'partner_id': data.get('partner_id'),
            'points': data.get('earned_points') or 0.0,
            'referral_partner_id': data.get('ref_customer') or False,
        }
        if data.get('earned_points'):
            self.env['pos.earn.loyalty'].create(loyalty_vals)

        if data.get('redeem_points'):
            del loyalty_vals['referral_partner_id']
            loyalty_vals.update({
                'points': data.get('redeem_points') or False,
                'points_amount': data.get('points_amount') or False
            })
            self.env['pos.redeem.loyalty'].create(loyalty_vals)

        flag = False
        if data.get('ref_customer'):
            if data.get('referral_event') == 'first_purchase':
                query = """
                    SELECT 
                        COUNT(id) 
                    FROM 
                        pos_earn_loyalty 
                    WHERE 
                        referral_partner_id = %s AND 
                        partner_id=%s""" % (data.get('ref_customer'), data.get('partner_id'))
                self.env.cr.execute(query)
                result = self.env.cr.dictfetchall()
                if result[0]['count'] == 1:
                    flag = True

            if data.get('referral_event') == 'every_purchase':
                flag = True

        if flag and data.get('ref_reward'):
            loyalty_vals.update({'partner_id': data.get('ref_customer'),
                                 'points': data.get('ref_reward') or 0.0,
                                 'referral_partner_id': False})
            self.env['pos.earn.loyalty'].create(loyalty_vals)

    def gift_voucher_management(self, data):
        voucher_redeem_details = data.get('voucher_redeem')
        self.env['aspl.gift.voucher.redeem'].create(voucher_redeem_details)

    def gift_card_management(self, data, pos_order_id):
        for create_details in data.get('giftcard'):
            if create_details.get("expire_date") and create_details.get("customer_id"):
                self.env['aspl.gift.card'].create(create_details)
        if data.get('redeem') and pos_order_id:
            redeem_details = data.get('redeem')
            redeem_vals = {
                'pos_order_id': pos_order_id.id,
                'order_date': pos_order_id.date_order,
                'customer_id': redeem_details.get('card_customer_id') or False,
                'card_id': redeem_details.get('redeem_card_no'),
                'amount': redeem_details.get('redeem_card_amount'),
            }
            use_giftcard = self.env['aspl.gift.card.use'].create(redeem_vals)
            if use_giftcard:
                use_giftcard.card_id.write({'card_value': use_giftcard.card_id.card_value - use_giftcard.amount})

        # recharge giftcard
        if data.get('recharge'):
            recharge_details = data.get('recharge')
            recharge_vals = {
                'user_id': pos_order_id.user_id.id,
                'recharge_date': pos_order_id.date_order,
                'customer_id': recharge_details.get('card_customer_id') or False,
                'card_id': recharge_details.get('recharge_card_id'),
                'amount': recharge_details.get('recharge_card_amount'),
            }
            recharge_giftcard = self.env['aspl.gift.card.recharge'].create(recharge_vals)
            if recharge_giftcard:
                recharge_giftcard.card_id.write(
                    {'card_value': recharge_giftcard.card_id.card_value + recharge_giftcard.amount})

    def wallet_management(self, data, pos_order_id):
        if data.get('change_amount_for_wallet'):
            session_id = pos_order_id.session_id
            cash_register_id = session_id.cash_register_id
            if not cash_register_id:
                raise Warning(_('There is no cash register for this PoS Session'))
            cash_bocx_out_obj = self.env['cash.box.out'].create(
                {'name': 'Credit', 'amount': data.get('change_amount_for_wallet')})
            cash_bocx_out_obj.with_context({'partner_id': pos_order_id.partner_id.id})._run(cash_register_id)
            vals = {
                'customer_id': pos_order_id.partner_id.id,
                'type': data.get('wallet_type'),
                'order_id': pos_order_id.id,
                'credit': data.get('change_amount_for_wallet'),
                'cashier_id': data.get('user_id'),
            }
            self.env['wallet.management'].create(vals)
        elif data.get('used_amount_from_wallet'):
            vals = {
                'customer_id': pos_order_id.partner_id.id,
                'type': data.get('wallet_type'),
                'order_id': pos_order_id.id,
                'debit': data.get('used_amount_from_wallet'),
                'cashier_id': data.get('user_id'),
            }
            self.env['wallet.management'].create(vals)
        else:
            vals = {
                'customer_id': pos_order_id.partner_id.id,
                'order_id': pos_order_id.id,
                'credit': data.get('lines')[0][2].get('price_subtotal_incl'),
                'cashier_id': data.get('user_id'),
            }
            self.env['wallet.management'].create(vals)

    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        if ui_order and ui_order.get('refund_order') and ui_order.get('refund_ref_order') and ui_order.get(
                'refund_ref_order'):
            reference_order_id = self.search([('pos_reference', '=', ui_order.get('refund_ref_order').get('name'))],
                                             limit=1)
            for line in ui_order.get('refund_ref_order').get('lines'):
                reference_order_line_id = self.env['pos.order.line'].browse(line[2].get('id'))
                if reference_order_line_id:
                    quantity = reference_order_line_id.order_return_qty - float(line[2].get('return_qty'))
                    reference_order_line_id.order_return_qty = quantity
                    return_lot_name = []
                    if line[2].get('select_operation_lot_name'):
                        for lot_line in line[2].get('select_operation_lot_name'):
                            return_lot_name.append(lot_line.get('lot_name'))
                        return_lot_ids = reference_order_line_id.mapped('return_pack_lot_ids').filtered(
                            lambda lot: lot.lot_name in return_lot_name)
                        for return_lot_id in return_lot_ids:
                            reference_order_line_id.return_pack_lot_ids = [(3, return_lot_id.id)]
                        reference_order_line_id._onchange_qty()
                        reference_order_line_id._onchange_amount_line_all()

            res.update({
                'name': reference_order_id.name + " REFUND",
                'back_order_reference': ui_order.get('refund_ref_order').get('name'),
            })
        if ui_order.get('selected_doctor'):
            res.update({
                'ref_doctor_id': ui_order.get('selected_doctor')['id'],
            })
        if ui_order.get('rating') != 'None':
            res.update({
                'rating': str(ui_order.get('rating')),
            })
        res.update({
            'change_amount_for_wallet': ui_order.get('change_amount_for_wallet') or 0.00,
            'amount_due': ui_order.get('amount_due'),
            'sales_person_id': ui_order.get('sales_person_id') or False,
            'signature': ui_order.get('sign') or False,
            'note': ui_order.get('order_note', False),
            'salesman_id': ui_order.get('salesman_id') or False,
            'user_id': ui_order.get('cashier_id') or False,
        })
        return res

    def write(self, vals):
        for order in self:
            if order.name == '/':
                vals['name'] = order.config_id.sequence_id._next()
        res = super(PosOrder, self).write(vals)
        return res

    @api.model
    def get_customer_product_history(self, product_id, partner_id):
        sql = """
            SELECT 
                po.name,
                pol.product_id,to_char(po.date_order, 'DD-MM-YYYY') AS date_order,
                pol.price_subtotal_incl AS total, 
                pol.qty ,
                uom.name AS uom_name 
            FROM 
                pos_order AS po
                LEFT JOIN pos_order_line AS pol ON pol.order_id = po.id 
                LEFT JOIN uom_uom AS uom ON pol.uom_id = uom.id 
            WHERE 
                pol.product_id = %s AND 
                po.partner_id = %s AND
                po.back_order_reference is null or po.back_order_reference = ''
            ORDER BY 
                po.date_order Desc 
            LIMIT 1
            """ % (product_id, partner_id)
        self.env.cr.execute(sql)
        res_all = self.env.cr.dictfetchall()
        return res_all

    @api.model
    def get_all_product_history(self, product_ids, partner_id):
        sql = """
            SELECT 
                po.name, 
                po.partner_id, 
                pol.product_id,
                pol.qty, 
                uom.name AS uom_name ,
                pol.price_subtotal_incl, 
                to_char(po.date_order, 'DD-MM-YYYY') AS date_order 
            FROM 
                pos_order_line AS pol
                INNER JOIN pos_order AS po ON po.id = pol.order_id 
                INNER JOIN uom_uom AS uom ON pol.uom_id = uom.id 
            WHERE 
                po.date_order = ( 
                    SELECT MAX (date_order) 
                    FROM pos_order 
                    WHERE partner_id IN ('%s'))
                and po.back_order_reference is null or po.back_order_reference = ''
            """ % partner_id
        self.env.cr.execute(sql)
        res_all_last_purchase_history = self.env.cr.dictfetchall()
        if len(res_all_last_purchase_history) > 0:
            res_single_date_purchase_history = res_all_last_purchase_history[0].get('date_order')
            res_single_order_name_purchase_history = res_all_last_purchase_history[0].get('name')
            sql = """
                SELECT 
                    DISTINCT ON (pol.product_id) pol.product_id, 
                    to_char(po.date_order, 'DD-MM-YYYY') AS date_order, 
                    pol.qty, 
                    po.name, 
                    uom.name AS uom_name,
                    Round(pol.price_subtotal_incl,2) AS price_subtotal_incl 
                FROM 
                    pos_order_line AS pol
                    INNER JOIN uom_uom AS uom ON pol.uom_id = uom.id 
                    INNER JOIN pos_order AS po on po.id = pol.order_id
                WHERE 
                    pol.product_id IN (%s) AND po.partner_id = %s 
                    AND po.back_order_reference is null or po.back_order_reference = ''
                ORDER BY 
                    pol.product_id, po.date_order DESC
                """ % (','.join(map(str, product_ids)), partner_id)
            self.env.cr.execute(sql)
            res_all_product_history = self.env.cr.dictfetchall()
            res_all = {
                'res_product_history': res_all_product_history,
                'res_last_purchase_history': res_all_last_purchase_history,
                'date_order': res_single_date_purchase_history,
                'order_name': res_single_order_name_purchase_history
            }
            return res_all
        return False

    @api.model
    def order_summary_report(self, val):
        order_vals = {}
        category_list = {}
        payment_list = {}
        domain = []
        count = 0.00
        amount = 0.00
        if val.get('session_id'):
            domain = [('session_id.id', '=', val.get('session_id'))]
        else:
            local = pytz.timezone(self.env.user.tz)
            start_date = val.get('start_date') + " 00:00:00"
            start_date_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            start_local_dt = local.localize(start_date_time, is_dst=None)
            start_utc_dt = start_local_dt.astimezone(pytz.utc)
            string_utc_date_time = start_utc_dt.strftime('%Y-%m-%d %H:%M:%S')

            end_date = val.get('end_date') + " 23:59:59"
            end_date_time = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            end_local_dt = local.localize(end_date_time, is_dst=None)
            end_utc_dt = end_local_dt.astimezone(pytz.utc)
            string_end_utc_date_time = end_utc_dt.strftime('%Y-%m-%d %H:%M:%S')
            domain = [('date_order', '>=', string_utc_date_time), ('date_order', '<=', string_end_utc_date_time)]
        if val.get('state'):
            domain += [('state', '=', val.get('state'))]
        orders = self.search(domain)
        if 'order_summary_report' in val.get('summary') or len(val.get('summary')) == 0:
            if val.get('state'):
                order_vals[val.get('state')] = []
            else:
                for order_state in orders.mapped('state'):
                    order_vals[order_state] = []
            for each_order in orders:
                user_tz = self.env.user.tz
                order_date_tz = each_order.date_order.astimezone(pytz.timezone(user_tz))
                if each_order.state in order_vals:
                    order_vals[each_order.state].append({
                        'order_ref': each_order.name,
                        'order_date': order_date_tz,
                        'total': float(format(each_order.amount_total, '.2f'))
                    })
                else:
                    order_vals.update({
                        each_order.state.append({
                            'order_ref': each_order.name,
                            'order_date': order_date_tz,
                            'total': float(format(each_order.amount_total, '.2f'))
                        })
                    })
        if 'category_summary_report' in val['summary'] or len(val['summary']) == 0:
            if val.get('state'):
                category_list[val.get('state')] = {}
            else:
                for each_order in orders.mapped('state'):
                    category_list[each_order] = {}
            for order_line in orders.mapped('lines'):
                if order_line.order_id.state == 'paid':
                    if order_line.product_id.pos_categ_id.name in category_list[order_line.order_id.state]:
                        count = category_list[order_line.order_id.state][order_line.product_id.pos_categ_id.name][0]
                        amount = category_list[order_line.order_id.state][order_line.product_id.pos_categ_id.name][1]
                        count += order_line.qty
                        amount += order_line.price_subtotal_incl
                    else:
                        count = order_line.qty
                        amount = order_line.price_subtotal_incl
                if order_line.order_id.state == 'done':
                    if order_line.product_id.pos_categ_id.name in category_list[order_line.order_id.state]:
                        count = category_list[order_line.order_id.state][order_line.product_id.pos_categ_id.name][0]
                        amount = category_list[order_line.order_id.state][order_line.product_id.pos_categ_id.name][1]
                        count += order_line.qty
                        amount += order_line.price_subtotal_incl
                    else:
                        count = order_line.qty
                        amount = order_line.price_subtotal_incl
                if order_line.order_id.state == 'invoiced':
                    if order_line.product_id.pos_categ_id.name in category_list[order_line.order_id.state]:
                        count = category_list[order_line.order_id.state][order_line.product_id.pos_categ_id.name][0]
                        amount = category_list[order_line.order_id.state][order_line.product_id.pos_categ_id.name][1]
                        count += order_line.qty
                        amount += order_line.price_subtotal_incl
                    else:
                        count = order_line.qty
                        amount = order_line.price_subtotal_incl
                category_list[order_line.order_id.state].update(
                    {order_line.product_id.pos_categ_id.name: [count, amount]})
                if False in category_list[order_line.order_id.state]:
                    category_list[order_line.order_id.state]['others'] = category_list[order_line.order_id.state].pop(
                        False)
        if 'payment_summary_report' in val['summary'] or len(val['summary']) == 0:
            if val.get('state'):
                payment_list[val.get('state')] = {}
            else:
                for each_order in orders.mapped('state'):
                    payment_list[each_order] = {}
            for payment_line in orders.mapped('payment_ids'):
                if payment_line.pos_order_id.state == 'paid':
                    if payment_line.payment_method_id.name in payment_list[payment_line.pos_order_id.state]:
                        count = payment_list[payment_line.pos_order_id.state][payment_line.payment_method_id.name]
                        count += payment_line.amount
                    else:
                        count = payment_line.amount
                if payment_line.pos_order_id.state == 'done':
                    if payment_line.payment_method_id.name in payment_list[payment_line.pos_order_id.state]:
                        count = payment_list[payment_line.pos_order_id.state][payment_line.payment_method_id.name]
                        count += payment_line.amount
                    else:
                        count = payment_line.amount
                if payment_line.pos_order_id.state == 'invoiced':
                    if payment_line.payment_method_id.name in payment_list[payment_line.pos_order_id.state]:
                        count = payment_list[payment_line.pos_order_id.state][payment_line.payment_method_id.name]
                        count += payment_line.amount
                    else:
                        count = payment_line.amount
                payment_list[payment_line.pos_order_id.state].update(
                    {payment_line.payment_method_id.name: float(format(count, '.2f'))})
        return {
            'order_report': order_vals,
            'category_report': category_list,
            'payment_report': payment_list,
            'state': val['state'] or False
        }

    @api.model
    def product_summary_report(self, val):
        product_summary_dict = {}
        category_summary_dict = {}
        payment_summary_dict = {}
        location_summary_dict = {}
        if val.get('session_id'):
            domain = [('session_id.id', '=', val.get('session_id'))]
        else:
            local = pytz.timezone(self.env.user.tz)
            start_date = val.get('start_date') + " 00:00:00"
            start_date_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            start_local_dt = local.localize(start_date_time, is_dst=None)
            start_utc_dt = start_local_dt.astimezone(pytz.utc)
            string_utc_date_time = start_utc_dt.strftime('%Y-%m-%d %H:%M:%S')

            end_date = val.get('end_date') + " 23:59:59"
            end_date_time = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            end_local_dt = local.localize(end_date_time, is_dst=None)
            end_utc_dt = end_local_dt.astimezone(pytz.utc)
            string_end_utc_date_time = end_utc_dt.strftime('%Y-%m-%d %H:%M:%S')

            domain = [('date_order', '>=', string_utc_date_time), ('date_order', '<=', string_end_utc_date_time)]
        order_detail = self.search(domain)
        if order_detail:
            if 'product_summary' in val.get('summary') or len(val.get('summary')) == 0:
                for each_order_line in order_detail.mapped('lines'):
                    if each_order_line.product_id.name in product_summary_dict:
                        product_qty = product_summary_dict[each_order_line.product_id.name]
                        product_qty += each_order_line.qty
                    else:
                        product_qty = each_order_line.qty
                    product_summary_dict[each_order_line.product_id.name] = product_qty

            if 'category_summary' in val.get('summary') or len(val.get('summary')) == 0:
                for each_order_line in order_detail.mapped('lines'):
                    if each_order_line.product_id.pos_categ_id.name in category_summary_dict:
                        category_qty = category_summary_dict[each_order_line.product_id.pos_categ_id.name]
                        category_qty += each_order_line.qty
                    else:
                        category_qty = each_order_line.qty
                    category_summary_dict[each_order_line.product_id.pos_categ_id.name] = category_qty
                if False in category_summary_dict:
                    category_summary_dict['Others'] = category_summary_dict.pop(False)

            if 'payment_summary' in val.get('summary') or len(val.get('summary')) == 0:
                for payment_line in order_detail.mapped('payment_ids'):
                    if payment_line.payment_method_id.name in payment_summary_dict:
                        payment = payment_summary_dict[payment_line.payment_method_id.name]
                        payment += payment_line.amount
                    else:
                        payment = payment_line.amount
                    payment_summary_dict[payment_line.payment_method_id.name] = float(format(payment, '2f'))

            if 'location_summary' in val.get('summary') or len(val.get('summary')) == 0:
                stock_picking_data = self.env['stock.picking'].sudo().search([('pos_session_id', 'in',
                                                                               order_detail.mapped('session_id').ids)])
                if stock_picking_data:
                    for each_stock in stock_picking_data:
                        location_summary_dict[each_stock.location_id.name] = {}
                    # for each_stock in stock_picking_data:
                    for each_stock_line in stock_picking_data.mapped('move_ids_without_package'):
                        if each_stock_line.product_id.name in \
                                location_summary_dict[each_stock_line.picking_id.location_id.name]:
                            location_qty = location_summary_dict[each_stock_line.picking_id.location_id.name][
                                each_stock_line.product_id.name]
                            location_qty += each_stock_line.quantity_done
                        else:
                            location_qty = each_stock_line.quantity_done
                        location_summary_dict[each_stock_line.picking_id.location_id.name][
                            each_stock_line.product_id.name] = location_qty
        return {
            'product_summary': product_summary_dict,
            'category_summary': category_summary_dict,
            'payment_summary': payment_summary_dict,
            'location_summary': location_summary_dict,
        }

    @api.model
    def prepare_payment_summary_data(self, row_data, key):
        payment_details = {}
        summary_data = {}

        for each in row_data:
            if key == 'journals':
                payment_details.setdefault(each['month'], {})
                payment_details[each['month']].update({each['name']: each['amount']})
                summary_data.setdefault(each['name'], 0.0)
                summary_data.update({each['name']: summary_data[each['name']] + each['amount']})
            else:
                payment_details.setdefault(each['login'], {})
                payment_details[each['login']].setdefault(each['month'], {each['name']: 0})
                payment_details[each['login']][each['month']].update({each['name']: each['amount']})

        return [payment_details, summary_data]

    @api.model
    def payment_summary_report(self, vals):
        sql = False
        final_data_dict = dict.fromkeys(
            ['journal_details', 'salesmen_details', 'summary_data'], {})
        current_time_zone = self.env.user.tz or 'UTC'
        if vals.get('session_id'):
            if vals.get('summary') == 'journals':
                sql = """ SELECT
                        REPLACE(CONCAT(to_char(to_timestamp(
                        EXTRACT(month FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')::text, 'MM'),'Month'),
                        '-',EXTRACT(year FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')),
                        ' ', '') AS month,
                        ppm.name, ppm.id,
                        SUM(pp.amount) AS amount
                        FROM pos_payment AS pp
                        INNER JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
                        WHERE session_id = %s
                        GROUP BY month, ppm.name, ppm.id
                        ORDER BY month ASC
                    """ % (current_time_zone, current_time_zone, vals.get('session_id'))
            if vals.get('summary') == 'sales_person':
                sql = """ SELECT
                        REPLACE(CONCAT(to_char(to_timestamp(
                        EXTRACT(month FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')::text, 'MM'), 'Month'), 
                        '-',EXTRACT(year FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')),
                        ' ', '') AS month,
                        rp.name AS login, ppm.name, SUM(pp.amount) AS amount
                        FROM
                        pos_order AS po
                        INNER JOIN res_users AS ru ON ru.id = po.user_id
                        INNER JOIN res_partner AS rp ON rp.id = ru.partner_id
                        INNER JOIN pos_payment AS pp ON pp.pos_order_id = po.id
                        INNER JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
                        WHERE
                        po.session_id = %s
                        GROUP BY ppm.name, rp.name, month
                     """ % (current_time_zone, current_time_zone, vals.get('session_id'))
        else:
            local = pytz.timezone(self.env.user.tz)
            start_date = val.get('start_date') + " 00:00:00"
            start_date_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            start_local_dt = local.localize(start_date_time, is_dst=None)
            start_utc_dt = start_local_dt.astimezone(pytz.utc)
            string_utc_date_time = start_utc_dt.strftime('%Y-%m-%d %H:%M:%S')

            end_date = val.get('end_date') + " 23:59:59"
            end_date_time = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            end_local_dt = local.localize(end_date_time, is_dst=None)
            end_utc_dt = end_local_dt.astimezone(pytz.utc)
            string_end_utc_date_time = end_utc_dt.strftime('%Y-%m-%d %H:%M:%S')
            
            s_date, e_date = start_end_date_global(string_utc_date_time, string_end_utc_date_time, current_time_zone)
            if vals.get('summary') == 'journals':
                sql = """ SELECT
                        REPLACE(CONCAT(to_char(to_timestamp(
                        EXTRACT(month FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')::text, 'MM'),'Month'),
                        '-',EXTRACT(year FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')),
                        ' ', '') AS month,
                        ppm.name, ppm.id,
                        SUM(pp.amount) AS amount
                        FROM pos_payment AS pp
                        INNER JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
                        WHERE payment_date BETWEEN  '%s' AND '%s'
                        GROUP BY month, ppm.name, ppm.id
                        ORDER BY month ASC
                     """ % (current_time_zone, current_time_zone, s_date, e_date)

            if vals.get('summary') == 'sales_person':
                sql = """ SELECT
                        REPLACE(CONCAT(to_char(to_timestamp(
                        EXTRACT(month FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')::text, 'MM'), 'Month'), 
                        '-',EXTRACT(year FROM pp.payment_date AT TIME ZONE 'UTC' AT TIME ZONE '%s')),
                        ' ', '') AS month,
                        rp.name AS login, ppm.name, SUM(pp.amount) AS amount
                        FROM
                        pos_order AS po
                        INNER JOIN res_users AS ru ON ru.id = po.user_id
                        INNER JOIN res_partner AS rp ON rp.id = ru.partner_id
                        INNER JOIN pos_payment AS pp ON pp.pos_order_id = po.id
                        INNER JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
                        WHERE
                        po.date_order BETWEEN '%s' AND '%s'
                        GROUP BY ppm.name, rp.name, month
                      """ % (current_time_zone, current_time_zone, s_date, e_date)
        if sql:
            self._cr.execute(sql)
            sql_result = self._cr.dictfetchall()

            if sql_result:
                result = self.prepare_payment_summary_data(sql_result, vals.get('summary'))
                if vals.get('summary') == 'journals':
                    final_data_dict.update({'journal_details': result[0], 'summary_data': result[1]})
                    return final_data_dict
                else:
                    final_data_dict.update({'salesmen_details': result[0]})
                    return final_data_dict
            else:
                return final_data_dict
        else:
            return final_data_dict

    @api.model
    def create(self, values):
        res = super(PosOrder, self).create(values)
        member_lst = []
        tax = res.env['ir.config_parameter'].sudo().get_param('flexipharmacy.pos_commission_with')
        if res.commission_calculation == 'product':
            for line in res.lines:
                for lineid in line.product_id.pos_product_commission_ids:
                    lines = {'doctor_id': res.ref_doctor_id.id}
                    if res.commission_based_on == 'product_sell_price':
                        if tax == 'without_tax':
                            lines['amount'] = line.price_subtotal * lineid.commission / 100 if lineid.calculation == 'percentage'\
                                              else lineid.commission * line.qty
                        else:
                            lines['amount'] = line.price_subtotal_incl * lineid.commission / 100 if lineid.calculation == 'percentage'\
                                              else lineid.commission * line.qty
                    else:
                        if tax == 'without_tax':
                            lines['amount'] = (line.price_subtotal - (line.product_id.standard_price * line.qty)) * lineid.commission / 100\
                                              if lineid.calculation == 'percentage' else lineid.commission * line.qty
                        else:
                            lines['amount'] = (line.price_subtotal_incl - (line.product_id.standard_price * line.qty)) * lineid.commission / 100\
                                              if lineid.calculation == 'percentage' else lineid.commission * line.qty
                    member_lst.append(lines)
                    break

        elif res.commission_calculation == 'product_category':
            for line in res.lines:
                for lineid in line.product_id.pos_categ_id.pos_category_comm_ids:
                    lines = {'doctor_id': res.ref_doctor_id.id}
                    if res.commission_based_on == 'product_sell_price':
                        if tax == 'without_tax':
                            lines['amount'] = line.price_subtotal * lineid.commission / 100 if lineid.calculation == 'percentage' else lineid.commission * line.qty
                        else:
                            lines['amount'] = line.price_subtotal_incl * lineid.commission / 100 if lineid.calculation == 'percentage' else lineid.commission * line.qty
                    else:
                        if tax == 'without_tax':
                            lines['amount'] = (line.price_subtotal - (
                                        line.product_id.standard_price * line.qty)) * lineid.commission / 100 \
                                        if lineid.calculation == 'percentage' else lineid.commission * line.qty
                        else:
                            lines['amount'] = (line.price_subtotal_incl - (
                                        line.product_id.standard_price * line.qty)) * lineid.commission / 100 \
                                        if lineid.calculation == 'percentage' else lineid.commission * line.qty
                    member_lst.append(lines)
                    break

        elif res.commission_calculation == 'doctor':
            for line in res.lines:
                for lineid in res.ref_doctor_id.pos_doctor_commission_ids:
                    lines = {'doctor_id': res.ref_doctor_id.id}
                    if res.commission_based_on == 'product_sell_price':
                        if tax == 'without_tax':
                            lines['amount'] = line.price_subtotal * lineid.commission / 100 \
                                if lineid.calculation == 'percentage' else lineid.commission * line.qty
                        else:
                            lines['amount'] = line.price_subtotal_incl * lineid.commission / 100 \
                                if lineid.calculation == 'percentage' else lineid.commission * line.qty
                    else:
                        if tax == 'without_tax':
                            lines['amount'] = (line.price_subtotal - (
                                        line.product_id.standard_price * line.qty)) * lineid.commission / 100 \
                                        if lineid.calculation == 'percentage' else lineid.commission * line.qty
                        else:
                            lines['amount'] = (line.price_subtotal_incl - (
                                        line.product_id.standard_price * line.qty)) * lineid.commission / 100 if lineid.calculation == 'percentage' else lineid.commission * line.qty
                    member_lst.append(lines)
                    break

        user_by = {}
        for member in member_lst:
            if member['doctor_id'] in user_by:
                user_by[member['doctor_id']]['amount'] += member['amount']
            else:
                user_by.update({member['doctor_id']: member})
        member_lst = []
        for user in user_by:
            member_lst.append((0, 0, user_by[user]))
        res.sale_commission_ids = member_lst

        if res.ref_doctor_id:
            if res.sale_commission_ids.amount > 0:
                doctor_detail = {'doctor_id': res.ref_doctor_id.id,
                                'name': res.name,
                                'commission_date': date.today(),
                                'state': 'draft',
                                'amount': res.sale_commission_ids.amount,
                                'order_id': res.id
                                }
                self.env['pos.doctor.commission'].create(doctor_detail)
        return res


class ReturnPosOrderLineLot(models.Model):
    _name = "return.pos.pack.operation.lot"
    _description = "Return Specify product lot/serial number in pos order line"
    _rec_name = "lot_name"

    pos_order_line_id = fields.Many2one('pos.order.line')
    order_id = fields.Many2one('pos.order', related="pos_order_line_id.order_id", readonly=False)
    lot_name = fields.Char('Lot Name')
    product_id = fields.Many2one('product.product', related='pos_order_line_id.product_id', readonly=False)

    def _export_for_ui(self, lot):
        return {
            'lot_name': lot.lot_name,
        }

    def export_for_ui(self):
        return self.mapped(self._export_for_ui) if self else []


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    uom_id = fields.Many2one('uom.uom', string="UOM")
    line_note = fields.Char('Comment', size=512)
    active_ingredients = fields.Char('Ingredients')
    order_return_qty = fields.Float('Remaining Qty', digits='Product Unit of Measure', default=1)
    return_pack_lot_ids = fields.One2many('return.pos.pack.operation.lot', 'pos_order_line_id',
                                          string='Remaining Lot/serial')

    def _export_for_ui(self, orderline):
        return_pack_lot_ids = []
        vals = {
            'qty': orderline.qty,
            'order_return_qty': orderline.order_return_qty,
            'price_unit': orderline.price_unit,
            'price_subtotal': orderline.price_subtotal,
            'price_subtotal_incl': orderline.price_subtotal_incl,
            'product_id': orderline.product_id.id,
            'discount': orderline.discount,
            'line_note': orderline.line_note,
            'tax_ids': [[6, False, orderline.tax_ids.mapped(lambda tax: tax.id)]],
            'id': orderline.id,
            'pack_lot_ids': [[0, 0, lot] for lot in orderline.pack_lot_ids.export_for_ui()],
            'return_pack_lot_ids': [[0, 0, lot] for lot in orderline.return_pack_lot_ids.export_for_ui()],
        }
        if vals.get('return_pack_lot_ids'):
            pos_line_ids = self.search_read([('id', '=', vals.get('id'))])
            operation_lot_id = self.env['return.pos.pack.operation.lot'].search(
                [('id', 'in', pos_line_ids[0].get('return_pack_lot_ids'))])
            for operation_lot_name in operation_lot_id.mapped('display_name'):
                return_pack_lot_ids.append({'lot_name': operation_lot_name})
            vals['operation_lot_name'] = return_pack_lot_ids
        return vals

    def pos_order_line_read(self, line_ids):
        pos_line_ids = self.search_read([('id', 'in', line_ids)])
        for pos_line_id in pos_line_ids:
            pack_lot_ids = []
            operation_lot_id = self.env['pos.pack.operation.lot'].search(
                [('id', 'in', pos_line_id.get('pack_lot_ids'))])
            for operation_lot_name in operation_lot_id.mapped('display_name'):
                pack_lot_ids.append({'lot_name': operation_lot_name})
            pos_line_id['operation_lot_name'] = pack_lot_ids
        return pos_line_ids

    @api.model
    def create(self, vals):
        try:
            if vals.get('uom_id'):
                vals['uom_id'] = vals.get('uom_id')[0]
        except Exception:
            vals['uom_id'] = vals.get('uom_id') or None
            pass
        return super(PosOrderLine, self).create(vals)

class PosOrderCommission(models.Model):
    _name = 'pos.order.commission'
    _description = "Point of Sale Sales Commission"

    doctor_id = fields.Many2one('res.partner', domain="[('is_doctor', '=', True)]", string='Doctor')
    amount = fields.Float(string='Amount')
    pos_order_id = fields.Many2one('pos.order')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
