import ast
import json
import requests
import time
import hashlib
import hmac
import math
from datetime import datetime, timedelta
from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError

class TiktokGetOrder(models.TransientModel):
    _name = 'tiktok.get.order'
    _description = 'Tiktok Get Orders'

    is_synced = fields.Boolean('Synced', default=False)
    is_continue = fields.Boolean('Continue Last Sync Date', default=False)
    
    start_date = fields.Datetime('Start Date')
    shop_id = fields.Many2one('tiktok.shop', 'Shop')

    @api.onchange('shop_id')
    def onchange_shop_id(self):
        self.is_synced = False
        self.is_continue = False
        self.start_date = False
        history_obj = self.env['tiktok.history.api']
        last_history_id = history_obj.search([('name', '=', 'Get Order List'), ('shop_id', '=', self.shop_id.id), ('state', 'in', ['partial', 'success'])], limit=1)
        if last_history_id:
            self.is_synced = True
            self.is_continue = True
            self.start_date = False

    def action_confirm(self):
        print('TEST GET ORDER = = =')
        company_obj = self.env['res.company']
        product_obj = self.env['product.product']
        product_tmpl_obj = self.env['product.template']
        partner_obj = self.env['res.partner']
        carrier_obj = self.env['delivery.carrier']
        sale_obj = self.env['sale.order']
        line_obj = self.env['sale.order.line']
        picking_obj = self.env['stock.picking']
        warehouse_obj = self.env['stock.warehouse']
        return_obj = self.env['stock.return.picking']
        invoice_obj = self.env['account.move']
        inv_line_obj = self.env['account.move.line']
        register_obj = self.env['account.payment.register']
        payment_obj = self.env['account.payment']
        order_obj = self.env['tiktok.order']
        history_obj = self.env['tiktok.history.api']
        update_obj = self.env['tiktok.update.product']
        tiktok_product_obj = self.env['tiktok.product']
        tiktok_variant_obj = self.env['tiktok.product.variant']
        method_line_obj = self.env['account.payment.method.line']

        company = self.env.user.company_id
        company_id = company.id
        data = self
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('jys_tiktok.view_tiktok_history_api_popup')
        view_id = view_ref and view_ref[1] or False

        if not data.shop_id:
            raise UserError(_('Please select your shop!'))
        shop = data.shop_id

        if not shop.payment_journal_id:
            raise UserError(_('Please fill your shop\'s Payment Journal!'))
        if not shop.payment_method_id:
            raise UserError(_('Please fill your shop\'s Payment Method!'))
        if not company.tiktok_commission_product_id:
            raise UserError(_('Please fill your TikTok Commission Product!'))
        if not shop.start_date:
            raise UserError(_('Please fill in the Start Date for get order.'))
        if not company.tiktok_logistic_product_id:
            raise UserError(_('Please fill your TikTok Delivery Product!'))
        # if not company.tiktok_rebate_product_id:
        #     raise UserError(_('Please configure your Tiktok rebate product!'))
        # if not company.tiktok_tax_product_id:   
        #     raise UserError(_('Please configure your Tiktok tax product!'))

        cr = self.env.cr
        context = {}
        access_token = shop.tiktok_token
        tiktok_id = shop.shop_id
        chiper = str(shop.tiktok_chiper)
        domain = company.tiktok_api_domain
        app = company.tiktok_client_id
        key = company.tiktok_client_secret
        timest = int(time.time())

        def cancel_order(sale):
            is_cancel = False

            for inv in sale.invoice_ids:
                if inv.state not in ['cancel'] and inv.pament_state not in ['paid']:
                    inv.button_cancel()

            for picking in sale.picking_ids:
                if picking.picking_type_id.code == 'outgoing':
                    if picking.state == 'done':
                        is_cancel = True
                        if not picking.is_returned:
                            if not picking.is_returned:
                                default_data = return_obj.with_context(active_ids=[picking.id], active_id=picking.id).default_get(['move_dest_exists', 'original_location_id', 'product_return_moves', 'parent_location_id', 'location_id'])
                                return_wiz = return_obj.with_context(active_ids=[picking.id], active_id=picking.id).create(default_data)
                                return_wiz.product_return_moves.write({'to_refund': True}) # Return only 2
                                res = return_wiz.create_returns()
                                return_pick = picking_obj.browse(res['res_id'])
                                
                                if return_pick.show_check_availability == True:
                                    wiz_act = return_pick.with_context(confirm_from_wizard=True).action_assign()
                                    wiz_act = return_pick.with_context(confirm_from_wizard=True).action_done()
                                
                                else:
                                    wiz_act = return_pick.with_context(confirm_from_wizard=True).button_validate()
                                    wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
                                    wiz.with_context(confirm_from_wizard=True).process()

                                picking.write({
                                    'is_returned': True    
                                })
                        else:

                            if picking.state != 'cancel':
                                picking.action_cancel()

            if is_cancel:
                cr.execute("""
                    UPDATE sale_order SET state = 'cancel' WHERE id = %s
                """ % sale.id)

            else:            
                sale.action_cancel()

        def rts_order(sale, order):
            payment_date = False

            if order.get('paid_time',0):
                date_order = datetime.fromtimestamp(int(str(order.get('paid_time')))).strftime('%Y-%m-%d %H:%M:%S')
            
            max_ship_date = False
            if order.get('rts_sla_time',False):
                max_ship_date = datetime.fromtimestamp(int(order['rts_sla_time'])).strftime('%Y-%m-%d %H:%M:%S')
            sale_obj.write({
                'tiktok_payment_date': payment_date,
                'tiktok_max_ship_date': max_ship_date,
                'slowest_delivery_date': max_ship_date
            })
            if sale.state in ['draft', 'sent']:
                confirm_context = context.copy()
                confirm_context.update(is_tiktok_confirm=True)
                sale.with_context(confirm_context).action_confirm()

        def shipped_order(sale, order):
            if sale.tiktok_actual_shipping_cost != (float(order.get('payment').get('shipping_fee',0)) and abs(float(order.get('payment').get('shipping_fee',0))) or 0):
                sale.write({
                    'tiktok_actual_shipping_cost': float(order.get('payment').get('shipping_fee',0)) and abs(float(order.get('payment').get('shipping_fee',0))) or 0
                })

            ship_context = context.copy()
            ship_context.update(is_tiktok_ship=True)
            ship_context.update(confirm_from_wizard=True)

            for picking in sale.picking_ids:
                if picking.state not in ('draft', 'cancel', 'done'):
                    if picking.show_check_availability:
                        picking.with_context(ship_context).action_assign()
                    picking.with_context(ship_context).button_validate()

            # for picking in sale.picking_ids:
            #     print(picking.state,'STATE = = =')
            #     if picking.state not in ('draft', 'cancel', 'done'):
            #         print(picking.show_check_availability,'show_check_availability===')
            #         if picking.show_check_availability == True:
            #             wiz_act = picking.with_context(ship_context).action_assign()
            #             wiz_act = picking.button_validate()

            #         else:
            #             # wiz_act = picking.with_context(ship_context).button_validate()
            #             # wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
            #             # wiz.with_context(ship_context).process()
            #             wiz_act = picking.with_context(ship_context).action_assign()
            #             wiz_act = picking.button_validate()

        def create_invoice_order(sale):
            if sale.invoice_ids:
                for invoice in sale.invoice_ids:
                    if invoice.state == 'cancel':
                        invoice_id = sale._create_invoices()
                    else:
                        invoice_id = invoice
            else:
                invoice_id = sale._create_invoices()

            invoice = invoice_obj.browse(invoice_id.id)
            invoice.write({
                'invoice_date': sale.date_order,
                'is_tiktok': True,
            })

            if invoice.state not in ['posted', 'cancel']:
                invoice.action_post()
            
            return invoice_id

        def complete_order(invoice_id, sale, order):
            invoice = invoice_obj.browse(invoice_id)
            if invoice.state != 'paid':

                partner_updated = False
                if invoice.partner_id.parent_id:
                    partner_id = invoice.partner_id.parent_id.id

                else:
                    partner_id = invoice.partner_id.id

                if sale.carrier_id and not sale.carrier_id.is_cashless:
                    # shipping_cost = float(order.get('payment_info').get('shipping_fee',0))
                    # shipping_line_ids = line_obj.search([('order_id', '=', sale.id), ('product_id', '=', sale.carrier_id.product_id.id), ('price_unit', '!=', shipping_cost)])
                    
                    # if shipping_line_ids:
                    #     shipping_lines = shipping_line_ids
                        
                    #     for shipping_line in shipping_lines:
                    #         shipping_line.write({
                    #             'price_unit': shipping_cost
                    #         })

                    # invoice_line_ids = inv_line_obj.search([('invoice_id', '=', invoice.id), ('product_id', '=', sale.carrier_id.product_id.id), ('price_unit', '!=', shipping_cost)])
                    # if invoice_line_ids:
                    #     invoice.button_cancel()
                    #     invoice.write({'state': 'draft', 'date': sale.date_order,})
                    #     invoice_lines = invoice_line_ids
                        
                    #     for invoice_line in invoice_lines:
                    #         invoice_line.write({
                    #             'price_unit': shipping_cost,
                    #             'price_subtotal': shipping_cost  
                    #         })

                    #     if invoice.partner_id.parent_id:
                    #         invoice.write({'partner_id': partner_id,})
                    #         partner_updated = True
                    #     invoice.post()

                    if invoice.partner_id.parent_id:
                        invoice.write({'partner_id': partner_id,})
                        partner_updated = True
                    if invoice.state != 'posted':
                        invoice.action_post()

                if invoice.partner_id.parent_id and not partner_updated:
                    invoice.button_cancel()
                    invoice.write({'state': 'draft', 'date': sale.date_order,'partner_id': partner_id})
                    invoice.post()

                move_line_ids = []
                for line in invoice.move_id.line_ids:
                    if line.account_id.reconcile:
                        move_line_ids.append(line.id)

                ctx = dict(self._context, uid=self._uid, active_model='account.move', active_ids=[invoice.id], active_id=invoice.id)
                payment_method_line_id = method_line_obj.search([('payment_method_id.payment_type','=','inbound'),('journal_id','=',shop.payment_journal_id.id)], limit=1)
                payment_method_line_id = payment_method_line_id.id
                pay_id = register_obj.with_context(ctx).create({
                    'amount': invoice.amount_residual,
                    'journal_id': shop.payment_journal_id.id,
                    'payment_method_line_id': payment_method_line_id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': partner_id,
                    'payment_date': datetime.fromtimestamp(order['update_time']).strftime('%Y-%m-%d'),
                })
                payment_data = pay_id.action_create_payments()

        def await_ship_order(sale, order):
            if order.get('packages',False):
                if order.get('packages')[0].get('id',False):
                    package_id = order.get('packages')[0].get('id')
                    # path = '/fulfillment/202309/packages/{package_id}/ship'
                    ship_params = {
                        "handover_method": 'DROP_OFF' if shop.fulfillment == 'dropoff' else 'PICKUP',
                    }
                    url = domain+"/fulfillment/202309/packages/%s/ship?app_key=%s&access_token=%s&timestamp=%s&shop_cipher=%s"%(package_id,app,access_token,timest,chiper)
                    sign = company_obj.cal_sign(url, key, headers, ship_params)
                    url = domain+"/fulfillment/202309/packages/%s/ship?app_key=%s&access_token=%s&sign=%s&timestamp=%s&shop_cipher=%s"%(package_id,app,access_token,sign,timest,chiper)
                    res = requests.post(url, json=ship_params, headers=headers)
                    values = res.json()

                    return True
                else:
                    return False
            else:
                return False

        def tracking_number_order(order):
            tracking_no = False
            if order.get('status',0) == 100:
                return tracking_no
            if order.get('tracking_number',False):
                tracking_no = order.get('tracking_number')

            return tracking_no

        headers = {
            'x-tts-access-token': str(access_token), 
            "Content-type": "application/json"
        }

        history_id = False
        more = True
        count = 0
        skipped_count = 0
        next_cursor = ''
        affected_list = ''
        skipped_list = ''
        additional_info = ''
        list_order_params = {
            'shop_cipher': chiper,
            'page_size': 50
        }
        is_continue = False

        start_order_date = False
        if data.is_continue:
            start_history_id = history_obj.search([('name', '=', 'Get Order List'), ('shop_id', '=', shop.id), ('state', 'in', ['partial', 'success']), ('is_order_date', '=', True)], limit=1)
            if start_history_id:
                start_history = history_obj.browse(start_history_id.id)
                start_order_date = datetime.strptime(start_history.running_date, '%Y-%m-%d %H:%M:%S')
        else:
            # print(data.start_date,'START DATE = = = =', type(data.start_date))
            # start_order_date = datetime.strptime(data.start_date, '%Y-%m-%d %H:%M:%S')
            start_order_date = data.start_date

        if data.is_continue:
            last_history_id = history_obj.search([('name', '=', 'Get Order List'), ('shop_id', '=', shop.id), ('state', 'in', ['partial', 'success'])], limit=1)
            if last_history_id:
                last_history = history_obj.browse(last_history_id.id)
                date_to = datetime.fromtimestamp(last_history.timestamp) + timedelta(days=15) - timedelta(minutes=30)
                date_from = datetime.fromtimestamp(last_history.timestamp) - timedelta(minutes=30)
                update_time_from = int(time.mktime(date_from.timetuple()))
                update_time_to = int(time.mktime(date_to.timetuple()))

                list_order_params['update_time_from'] = update_time_from
                list_order_params['update_time_to'] = update_time_to
                history_timestamp = int(time.time()) > update_time_to and update_time_to or int(time.time())
                running_date = datetime.fromtimestamp(update_time_from).strftime('%Y-%m-%d %H:%M:%S')
                is_continue = True

        if not is_continue:
            # date_from = datetime.strptime(data.start_date, '%Y-%m-%d %H:%M:%S')
            date_from = data.start_date
            date_to = date_from + timedelta(days=3)
            create_time_from = int(time.mktime(date_from.timetuple()))
            create_time_to = int(time.mktime((date_to).timetuple()))
            list_order_params['create_time_from'] = create_time_from
            list_order_params['create_time_to'] = create_time_to
            history_timestamp = int(time.time()) > create_time_to and create_time_to or int(time.time())
            running_date = data.start_date

        while(more):
            if 'create_time_from' in list_order_params:
                date_from = list_order_params['create_time_from']
            else:
                date_from = list_order_params['update_time_from']
            if 'create_time_to' in list_order_params:
                date_to = list_order_params['create_time_to']
            else:
                date_to = list_order_params['update_time_to']

            # path = '/order/202309/orders/search'
            
            sign = ''
            if not next_cursor:
                url = domain+"/order/202309/orders/search?app_key=%s&access_token=%s&sign=%s&timestamp=%s&shop_cipher=%s&page_size=%s"%(app,access_token,sign,timest,chiper,50)
                sign = company_obj.cal_sign(url, key, headers, list_order_params)
                url = domain+"/order/202309/orders/search?app_key=%s&access_token=%s&sign=%s&timestamp=%s&shop_cipher=%s&page_size=%s"%(app,access_token,sign,timest,chiper,50)
            if next_cursor:
                list_order_params.update(page_token=next_cursor)
                url = domain+"/order/202309/orders/search?app_key=%s&access_token=%s&sign=%s&timestamp=%s&shop_cipher=%s&page_size=%s&page_token=%s"%(app,access_token,sign,timest,chiper,50,next_cursor)
                sign = company_obj.cal_sign(url, key, headers, list_order_params)
                url = domain+"/order/202309/orders/search?app_key=%s&access_token=%s&sign=%s&timestamp=%s&shop_cipher=%s&page_size=%s&page_token=%s"%(app,access_token,sign,timest,chiper,50,next_cursor)

            res = requests.post(url, json=list_order_params, headers=headers)
            values = res.json()

            if not values.get('data'):
                history_id = history_obj.create({
                    'name': 'Get Order List',
                    'shop_id': shop.id,
                    'additional_info': values.get('message'),
                    'timestamp': timest,
                    'state': 'failed',
                }).id
                return {
                    'name': 'History API',
                    'type': 'ir.actions.act_window',
                    'res_model': 'tiktok.history.api',
                    'res_id': history_id,
                    'view_mode': 'form',
                    'view_id': view_id,
                    'target': 'new'
                }
            else:
                for order in values.get('data').get('orders',[]):
                    # if order['order_status'] == 100:
                    #     order_status = 'UNPAID'
                    # elif order['order_status'] == 111:
                    #     order_status = 'AWAITING_SHIPMENT'
                    # elif order['order_status'] == 112:
                    #     order_status = 'AWAITING_COLLECTION'
                    # elif order['order_status'] == 114:
                    #     order_status = 'PARTIALLY_SHIPPING'
                    # elif order['order_status'] == 121:
                    #     order_status = 'IN_TRANSIT'
                    # elif order['order_status'] == 122:
                    #     order_status = 'DELIVERED'
                    # elif order['order_status'] == 130:
                    #     order_status = 'COMPLETED'
                    # elif order['order_status'] == 140:
                    #     order_status = 'CANCELLED'
                    # else:
                    #     order_status = 'NO_STATUS'
                    order_status = order['status']
                    order_exist = order_obj.search([('name', '=', order['id']), ('shop_id', '=', shop.id), ('order_status', '=', order_status)], limit=1)
                    if order_exist:
                        if skipped_count != 0:
                            skipped_list += '\n'
                        skipped_count += 1
                        skipped_list += 'Order [ %s ] status created' % (order['id'])
                        continue

                    order_values = {
                        'name': order['id'],
                        'shop_id': shop.id,
                        'order_status': order_status,
                        'update_time': order['update_time']
                    }
                    order_obj.create(order_values)
                    if count != 0:
                        affected_list += '\n'
                    count += 1
                    affected_list += str(order['id'])

            if not values.get('data').get('next_page_token'):
                history_id = history_obj.create({
                    'name': 'Get Order List',
                    'shop_id': shop.id,
                    'total_inserted': count,
                    'total_affected': count,
                    'total_skipped': skipped_count,
                    'affected_list': affected_list,
                    'skipped_list': skipped_list,
                    'timestamp': history_timestamp,
                    'state': 'success',
                })
                more = False

            if more:
                next_cursor = values['data']['next_page_token']

        cr.execute(""" 
            SELECT array_to_string(ARRAY(
                SELECT name FROM (
                    SELECT DISTINCT ON (name) name, update_time
                    FROM tiktok_order
                    WHERE shop_id = %s AND ((is_updated IS NULL OR is_updated = false) OR (is_job IS NULL OR is_job = false))
                    ORDER BY name, update_time DESC LIMIT 30
                ) sub ORDER BY update_time ASC
            ), ',') """ % (shop.id))
        order_ids = list(cr.fetchone()[0].split(','))
        # order_ids = ['578945001992194058']

        sale_ids = []
        updated_order_ids = []
        inserted_count = 0
        updated_count = 0
        affected_count = 0
        skipped_count = 0
        affected_list = ''
        skipped_list = ''
        log_line_values = []

        #GET ORDER DETAIL
        path = '/order/202309/orders'

        url = domain+"/order/202309/orders?app_key=%s&access_token=%s&timestamp=%s&sign=%s&shop_cipher=%s&ids=%s"%(app,access_token,timest,sign,chiper,','.join(order_ids))
        sign = company_obj.cal_sign(url, key, headers)
        url = domain+"/order/202309/orders?app_key=%s&access_token=%s&timestamp=%s&sign=%s&shop_cipher=%s&ids=%s"%(app,access_token,timest,sign,chiper,','.join(order_ids))
        
        res = requests.get(url, headers=headers)
        values = res.json()

        if not values.get('data'):
            history_id = history_obj.create({
                'name': 'Get Order',
                'shop_id': shop.id,
                'additional_info': values.get('message'),
                'timestamp': timest,
                'state': 'failed',
            }).id

            return {
                'name': 'History API',
                'type': 'ir.actions.act_window',
                'res_model': 'tiktok.history.api',
                'res_id': history_id,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': view_id,
                'target': 'new'
            }
            return False
        else:
            for order in values.get('data').get('orders',[]):
                sale_id = sale_obj.search([('tiktok_ordersn', '=', order['id']), ('tiktok_shop_id', '=', shop.id)], limit=1)
                fulfillment = False 

                if not sale_id and order['status'] == 'CANCELLED':
                    sale_id = sale_obj.search([('tiktok_ordersn', '=', order['id'])], limit=1)

                if not sale_id:
                    sale_id = sale_obj.search([('marketplace_no','ilike',order['id'])], limit=1)

                if sale_id:
                    sale = sale_id

                    shipping_fee = order.get('payment').get('shipping_fee',0)
                    tiktok_package_id = order.get('packages')[0].get('id','0')

                    name  = order.get('recipient_address').get('name',False)
                    phone = order.get('recipient_address').get('phone_number',False)
                    street = order.get('recipient_address').get('full_address',False)
                    date_order = datetime.fromtimestamp(int(order['create_time'])).strftime('%Y-%m-%d %H:%M:%S')
                    # sale.write({'tiktok_actual_shipping_cost': shipping_fee,'tiktok_package_id': tiktok_package_id})
                    sale.write({'tiktok_actual_shipping_cost': shipping_fee,'date_order':date_order, 'tiktok_package_id':tiktok_package_id})
                    if name != sale.partner_shipping_id.name:
                        sale.partner_shipping_id.write({'name': name})

                    if phone != sale.partner_shipping_id.phone:
                        sale.partner_shipping_id.write({'phone': phone})

                    name_carrier = order.get('shipping_provider',False)

                    carrier_id = carrier_obj.search([('name','=',name_carrier)], limit=1)
                    if carrier_id.id != sale.carrier_id.id:
                        sale.write({'carrier_id': carrier_id.id})
                    if order['status'] in ['AWAITING_SHIPMENT','PARTIALLY_SHIPPING','AWAITING_COLLECTION']:
                        fulfillment = await_ship_order(sale, order)

                    tracking_no = tracking_number_order(order)
                               
                    if sale.tracking_no != tracking_no:
                        sale.write({'tracking_no': tracking_no})

                    if sale.tracking_no and sale.tracking_no == tracking_no:
                        cr.execute('''UPDATE tiktok_order SET is_updated = True ,is_job = True WHERE name = %s''',(order['id'],))

                    if sale.state in ['draft', 'sent']:
                        if order['status'] == 'CANCELLED':
                            sale_ids.append(sale.id)
                            cancel_order(sale)
                        elif order['status'] in ['AWAITING_SHIPMENT','PARTIALLY_SHIPPING','AWAITING_COLLECTION']:
                            rts_order(sale, order)
                        elif order['status'] in ['IN_TRANSIT','DELIVERED']:
                            rts_order(sale, order)
                            shipped_order(sale, order)
                            invoice_id = create_invoice_order(sale)
                        elif order['status'] == 'COMPLETED':
                            rts_order(sale, order)
                            shipped_order(sale, order)
                            invoice_id = create_invoice_order(sale)
                            complete_order(invoice_id, sale, order)
                    elif sale.state in ['sale', 'done']:
                        if order['status'] == 'CANCELLED':
                            sale_ids.append(sale.id)
                            cancel_order(sale)
                        elif order['status'] in ['IN_TRANSIT','DELIVERED']:
                            shipped_order(sale, order)
                            invoice_id = create_invoice_order(sale)  
                        elif order['status'] == 'COMPLETED':
                            rts_order(sale, order)
                            shipped_order(sale, order)
                            invoice_id = create_invoice_order(sale)
                            complete_order(invoice_id, sale, order)

                    elif sale.state in ['cancel']:
                        if order['status'] == 'CANCELLED':
                            sale_ids.append(sale.id)
                            cancel_order(sale)

                    if sale.picking_ids:
                        for pick in sale.picking_ids:
                            pick.write({'carrier_tracking_ref': tracking_no})
                            
                    updated_count += 1

                else:
                    partner_invoice_id = partner_id = False
                    sale_exist = sale_obj.search([('tiktok_ordersn', '=', order['id'])], limit=1)
                    if len(str(order['create_time'])) > 12:
                        date_order = datetime.fromtimestamp(int(order['create_time'][:10])).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_order = datetime.fromtimestamp(order['create_time']).strftime('%Y-%m-%d %H:%M:%S')

                    if date_order < shop.start_date.strftime('%Y-%m-%d %H:%M:%S'):
                        update_order_ids = order_obj.search([('name', '=', order['id']), ('shop_id', '=', shop.id)])
                        if update_order_ids:
                            update_order_ids.write({
                                'is_updated': True,
                                'is_job': True
                            })
                        continue
                    is_tiktok_cod = False
                    if order.get('is_cod'):
                        is_tiktok_cod = True

                    if sale_exist:
                        update_order_ids = order_obj.search([('name', '=', order['id']), ('shop_id', '=', shop.id), ('update_time', '<=', order['update_time'])])
                        if update_order_ids:
                            update_order_ids.write({
                                'is_updated': True,
                                'is_job': True
                            })
                        if skipped_count != 0:
                            skipped_list += '\n'
                        skipped_count += 1
                        skipped_list += 'Order [ %s ] already created' % (order['id'])
                        continue

                    buyer_message = False
                    if order.get('buyer_message',False):
                        buyer_message = order.get('buyer_message',False)

                    sale_values = {
                        'partner_id': partner_id,
                        'date_order': date_order,
                        'tiktok_shop_id': shop.id,
                        'is_tiktok_order': True,
                        'tiktok_ordersn': order['id'],
                        'is_tiktok_cod': is_tiktok_cod,
                        'buyer_message': buyer_message,
                        'warehouse_id' : shop.setting_shop_id.id,
                        'client_order_ref': order['id'],
                        'marketplace_no': order['id']
                    }

                    name_carrier = order.get('shipping_provider',False)
                    if not name_carrier:
                        cr.execute('''UPDATE tiktok_order SET is_updated = True,is_job = True WHERE name = %s''',(order['id'],))
                        continue
                    carrier_id = carrier_obj.search([('name','=',name_carrier)], limit=1)
                    if carrier_id:
                        sale_values.update(carrier_id=carrier_id.id)
                    else:
                        carrier_id = carrier_obj.create({
                            'name': name_carrier,
                            'product_id': company.tiktok_logistic_product_id.id
                        })

                        sale_values.update(carrier_id=carrier_id.id)
                
                    partner_id = partner_obj.search([('is_tiktok_partner', '=', True), 
                        ('tiktok_username', '=', order.get('buyer_email',False)), ('name', '=', order.get('recipient_address').get('name',False)),
                        ('phone', '=', order.get('recipient_address').get('phone_number',False))], limit=1)
                    if partner_id:
                        partner_id = partner_id.id
                        partner_shipping_id = partner_obj.search([('is_tiktok_partner', '=', True), 
                        ('tiktok_username', '=', order.get('buyer_email',False)), ('name', '=', order.get('recipient_address').get('name',False)),
                        ('phone', '=', order.get('recipient_address').get('phone_number',False))], limit=1)
                        recipient = order['recipient_address']
                        if partner_shipping_id:
                            partner_shipping_id = partner_shipping_id.id
                        else:
                            address_city = ''
                            for dis in recipient.get('district_info',[]):
                                if dis.get('address_level_name') == 'city':
                                    address_city = dis.get('address_name')
                            partner_shipping_id = partner_obj.create({
                                'name': recipient['name'],
                                'phone': recipient['phone_number'],
                                'city': address_city,
                                'street': recipient['full_address'],
                                'zip': recipient['postal_code'],
                                'is_tiktok_partner': True,
                                'tiktok_username': order['buyer_email'],
                                'parent_id': partner_id,
                                'type': 'delivery',
                                'customer_rank': 1,
                                'supplier_rank': 0
                            }).id

                    else:
                        partner_id = partner_obj.create({
                            'name': order.get('recipient_address').get('name',False),
                            'phone': order.get('recipient_address').get('phone_number',False),
                            'is_tiktok_partner': True,
                            'tiktok_username': order['buyer_email'],
                        }).id
                        recipient = order['recipient_address']
                        address_city = ''
                        for dis in recipient.get('district_info',[]):
                            if dis.get('address_level_name') == 'city':
                                address_city = dis.get('address_name')
                        partner_shipping_id = partner_obj.search([('is_tiktok_partner', '=', True), 
                        ('tiktok_username', '=', order.get('buyer_email',False)), ('name', '=', order.get('recipient_address').get('name',False)),
                        ('phone', '=', order.get('recipient_address').get('phone_number',False)),('street','=',recipient['full_address'])], limit=1)

                        if partner_shipping_id:
                            partner_shipping_id = partner_shipping_id.id
                        else:
                            partner_shipping_id = partner_obj.create({
                                'name': recipient['name'],
                                'phone': recipient['phone_number'],
                                'city': address_city,
                                'street': recipient['full_address'],
                                'zip': recipient['postal_code'],
                                'is_tiktok_partner': True,
                                'tiktok_username': order['buyer_email'],
                                'parent_id': partner_id,
                                'type': 'delivery',
                                'customer_rank': 1,
                                'supplier_rank': 0
                            }).id

                    if partner_shipping_id:
                        sale_values['partner_shipping_id'] = partner_shipping_id 
                    if partner_id:
                        sale_values['partner_id'] = partner_id

                    comm_sum = 0
                    line_sum = 0
                    item_break = False
                    line_values_list = []
                    line_item_sku = {}
                    line_variation_sku = {}                                                                                                                                                
                    for line in order['line_items']:
                        if line['product_id']:
                            tiktok_variant_id = tiktok_variant_obj.search([('shop_id', '=', shop.id), ('variation_id', '=', line['product_id'])], limit=1)
                            if tiktok_variant_id:
                               
                                product_id = tiktok_variant_id.product_id.id
                                if product_id:
                                    product_id = tiktok_variant_id.product_id.id
                            else:
                                product_id = product_obj.search(['|',('default_code', '=', line['seller_sku']),('tiktok_variation_sku','=', line['seller_sku'])], limit=1)
                                if product_id:
                                    product_id = product_id.id
                                else:
                                    if skipped_count != 0:
                                        skipped_list += '\n'
                                    skipped_count += 1
                                  
                                    skipped_list += 'Get Order [ %s ] failed, product with SKU [ %s ] not found in system' % (order['id'], line['seller_sku'])
                                    item_break = True
                                    break
                        else:
                            tiktok_product_id = tiktok_product_obj.search([('shop_id', '=', shop.id), ('item_id', '=', line['product_id'])], limit=1)
                            if tiktok_product_id:
                                cr.execute(''' select product_tmpl_id from tiktok_product where id = %s ''',(tiktok_product_id.id,))
                                product_tmpl_id = map(lambda x: x[0], cr.fetchall())[0] or False
                            else:
                                if line['seller_sku']:
                                    product_tmpl_id = product_tmpl_obj.search([('tiktok_sku', '=', line['seller_sku'])], limit=1)
                                    if product_tmpl_id:
                                        product_tmpl_id = product_tmpl_id.id
                                    else:
                                        if skipped_count != 0:
                                            skipped_list += '\n'
                                        skipped_count += 1
                                    
                                        skipped_list += 'Get Order [ %s ] failed, product with SKU [ %s ] not found in system' % (order['id'], line['seller_sku'])
                                        item_break = True
                                        break
                                else:
                                    if skipped_count != 0:
                                        skipped_list += '\n'
                                    skipped_count += 1
                                    skipped_list += 'Get Order [ %s ] failed, product [ %s ] not found in system' % (order['id'], str(line['product_name']))
                                    item_break = True
                                    break

                            product_id = product_obj.search([('product_tmpl_id', '=', product_tmpl_id)], limit=1)
                            if not product_id:
                                if skipped_count != 0:
                                    skipped_list += '\n'
                                skipped_count += 1
                                skipped_list += 'Get Order [ %s ] failed, product with SKU [ %s ] has no variant' % (order['id'], line['seller_sku'])
                                item_break = True
                                break

                        if type(product_id) is list:    
                            product_id = product_id[0]
                        products = product_obj.browse(int(product_id))
                        print(products, products.name,'PRODUCT  = = = =\n')
                        variation_discounted_price = float(line['original_price']) - float(line['seller_discount'])
                        line_values = {
                            'name': products.name,
                            'product_id': products.id,
                            'product_uom_qty': 1 or line.get('quantity')
                        }
                        line_values.update(price_unit=variation_discounted_price)
                            
                        line_values_list.append(line_values)

                    combined_products = {}
                    for product in line_values_list:
                        product_id = product['product_id']
                        if product_id in combined_products:
                            combined_products[product_id]['product_uom_qty'] += product['product_uom_qty']
                        else:
                            combined_products[product_id] = product

                    line_values_list = list(combined_products.values())

                    if item_break:
                        continue 

                    create_context = context.copy()
                    create_context.update(is_tiktok_create=True) 
                    sale_id = sale_obj.with_context(create_context).create(sale_values)

                    if sale_id.date_order != date_order:
                        sale_id.write({'date_order': date_order})
                    sale_ids.append(sale_id)

                    total_weight = total_new_weight = 0
                    for line_values in line_values_list:
                        line_values.update(order_id=sale_id.id)
                        line_id = line_obj.with_context(create_context).create(line_values)
                        line_sum += line_id.price_subtotal
                        

                    shipping_cost = order.get('payment').get('shipping_fee',0)
                    # Hide tiktok_package_id
                    tiktok_package_id = order.get('packages')[0].get('id','0')

                    sale_id.write({
                        'delivery_rating_success': True,
                        'tiktok_actual_shipping_cost': shipping_cost,
                        'tiktok_package_id': tiktok_package_id
                    })
                    sale_id.set_delivery_line(carrier_id, 0)
                    carrier_line_id = line_obj.search([('order_id', '=', sale_id.id), ('is_delivery', '=', True)], limit=1)
                    if carrier_line_id:
                        carrier_line_id.unlink()
                        sale_id.write({'carrier_id': carrier_id.id,})

                    if order.get('status',False):
                        voucher_seller = (float(order.get('payment').get('original_total_product_price',0)) - float(order.get('payment').get('seller_discount',0)))*(shop.sales_fee/100) + shop.flat_fee
                        if voucher_seller >= 0:
                            line_values = {
                                'name': shop.tiktok_commission_product_id.name,
                                'order_id': sale_id.id,
                                'product_id': shop.tiktok_commission_product_id.id,
                                'product_uom_qty': 1
                            }
                            line_values.update(price_unit=-abs(voucher_seller))
                            line_id = line_obj.create(line_values)

                    sale = sale_id

                    if order['status'] == 'CANCELLED':
                        sale_ids.append(sale.id)
                        cancel_order(sale)
                    elif order['status'] in ['AWAITING_SHIPMENT','PARTIALLY_SHIPPING','AWAITING_COLLECTION']:
                        rts_order(sale, order)
                    elif order['status'] in ['IN_TRANSIT','DELIVERED']:
                        rts_order(sale, order)
                        shipped_order(sale, order)
                        invoice_id = create_invoice_order(sale)
                    elif order['status'] == 'COMPLETED':
                        rts_order(sale, order)
                        shipped_order(sale, order)
                        invoice_id = create_invoice_order(sale)
                        complete_order(invoice_id, sale, order)
                    inserted_count += 1

                if affected_count != 0:
                    affected_list += '\n'
                affected_count += 1
                affected_list += str(order['id'])
                update_order_ids = order_obj.search([('name', '=', order['id']), ('shop_id', '=', shop.id), ('update_time', '<=', order['update_time']),('is_updated','=',False)])
                if update_order_ids:
                    update_order_ids.write({
                        'is_updated': True,
                    })

                #if not dropoff and order['order_status'] in [111,112]:
                 #   if update_order_ids:
                  #      update_order_ids.write({
                   #         'is_updated': False,
                    #    })

        
        cr.execute(""" 
            SELECT COUNT(id) FROM tiktok_order 
                WHERE shop_id = %s AND (is_updated IS NULL OR is_updated = false) 
            """ % (shop.id))
        is_more = cr.fetchone()[0]
        additional_info = ''
        if is_more:
            context['is_more'] = True
            additional_info = 'There are still orders that need to be processed.'


        history_id = history_obj.create({
            'name': 'Get Order',
            'shop_id': shop.id,
            'additional_info': additional_info,
            'total_inserted': inserted_count,
            'total_updated': updated_count,
            'total_affected': affected_count,
            'total_skipped': skipped_count,
            'affected_list': affected_list,
            'skipped_list': skipped_list,
            'timestamp': timest,
            'state': 'success',
        }).id

        return {
            'name': 'History API',
            'type': 'ir.actions.act_window',
            'res_model': 'tiktok.history.api',
            'res_id': history_id,
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': context
        }
