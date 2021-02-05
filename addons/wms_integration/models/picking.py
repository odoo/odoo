# -*- coding: utf-8 -*-

import requests
from datetime import datetime
from odoo import _, fields, models
from odoo.tests import Form


class PickngWMS(models.Model):
    _inherit = "stock.picking"
    wms_order_id = fields.Char('wms_order_id', copy=False,
                               help="WMS orderID")
    wms_order_type = fields.Char('wms_order_type', copy=False,
                                 help="WMS order type")

    # @api.model
    def create(self, vals):
        res = super(PickngWMS, self).create(vals)
        return res

    def _get_warhouse_by_store(self, store_id):
        wh_model = self.env['stock.warehouse']
        whs = wh_model.search([('wms_warehouse_id', '=', store_id)])
        if whs:
            return whs[0]

    def action_cancel(self):
        cancelled = super(PickngWMS, self).action_cancel()
        if cancelled:
            wms = self.env['wms.extension']. \
                send_cancel_acceptance_by_pickings(self)

    def _send_acceptance_to_wms(self):
        picking = self.env['stock.picking']
        picking_to_send = picking.search([
            '&', ('wms_order_id', '=', False),
            ('state', '=', 'assigned'),
        ])

    def _get_products_by_product_ids(self, products):
        product_model = self.env['product.template']
        products_ids = product_model.search_read(
            [('wms_product_id', 'in', products)],
            ['product_variant_id', 'wms_product_id'])
        products_cleaned = {
            i['wms_product_id']: {
                'product_variant_id': i['product_variant_id'][0],
                'id': i['id']
            }
            for i in products_ids}
        return products_ids

    def _get_or_create_contractor(self, name):
        cont_model = self.env['res.partner']
        cont_ids = cont_model.search_read([('name', '=', name)], ['id'])
        if not cont_ids:
            contractor_id = cont_model.create({'name': name}).id
        else:
            contractor_id = cont_ids[0].get('id')
        return contractor_id

    def _create_or_update_purchace_order(self, order):
        order_id = order['order_id']
        store_id = order['store_id']
        external_id = order['external_id']
        purchase_order = self.env['purchase.order']
        pur_ids = purchase_order.search_read([('wms_order_id', '=', order_id)])
        if not pur_ids:
            start = datetime.now()
            doc_number = order['attr'].get('doc_number', order_id)
            contractor = order['attr'].get('contractor', 'Тестовый поставщик')
            contractor = self._get_or_create_contractor(contractor)
            created = order['created']
            updated = order['updated']
            wh = self._get_warhouse_by_store(store_id)
            if not wh:
                return

            reqired = order['required']
            products_ids = [
                i.get('product_id')
                for i in reqired
            ]
            products = self._get_products_by_product_ids(products_ids)
            order_line = []
            for product in products:
                count = 0
                price = 0.0
                for prod_wms in reqired:
                    if product['wms_product_id'] == prod_wms['product_id']:
                        count += prod_wms.get('count', 0)
                        price += float(prod_wms.get('price', 1)) / prod_wms.get(
                            'price_unit',
                            1)  # unit_amount |= prod_wms.get('unit_amount')
                order_line.append((
                    0, 0,
                    {
                        'product_id': product['product_variant_id'][0],
                        'product_qty': count,
                        'price_unit': price
                    }
                ))
            created = fields.datetime.fromisoformat(created)
            updated = fields.datetime.fromisoformat(updated)
            order_created = purchase_order.create({
                'partner_id': contractor,
                'order_line': order_line,
                'picking_type_id': wh.in_type_id.id,
                'name': doc_number,
                'date_order': created.strftime('%Y-%m-%d %H:%M:%S'),
                'date_planned': updated.strftime('%Y-%m-%d %H:%M:%S'),
                'wms_order_id': order['order_id'],
                'wms_order_type': 'acceptance'
            })
            finish = datetime.now()
            result = (finish - start)
            print(f'Purchase order created: {order_created.id} | time: {result.seconds}.{result.microseconds}')
            order_created.button_confirm()
            finish_confirm = datetime.now()
            result_confirn = (finish_confirm - start)
            print(f'Purchase order confirmed: {order_created.id} | time: {result_confirn.seconds}.{result_confirn.microseconds}')

    def _stowage_update(self, order):
        picking = None
        parent = order.get('parent')
        order_id = order['order_id']
        if parent:
            parent = parent[0]
        else:
            return
        dubl = self.search_read([('wms_order_id', '=', order_id)])
        if not dubl:
            start = datetime.now()
            purchase_order = self.env['purchase.order']
            pur_ids = purchase_order.search(
                [('wms_order_id', '=', parent)])
            if pur_ids:
                if pur_ids[0].picking_ids:
                    picking = pur_ids[0].picking_ids[0]
            if picking:
                picking.wms_order_id = order['order_id']
                picking.wms_order_type = order['type']
                wiz_act = picking.button_validate()
                wiz = Form(self.env[wiz_act['res_model']].with_context(
                    wiz_act['context'])).save()
                wiz.process()
                finish = datetime.now()
                result = (finish - start)
                print(f'Stowage confirmed: {picking.id} | time: {result.seconds}.{result.microseconds}')


    def _picking_processing(self):
        wms = self.env['wms.extension']
        wms_attrs = wms.get_wms_attrs()
        headers = wms_attrs.get('headers')
        cursor = wms_attrs.get('wms_order_cursor')
        if cursor == 'None':
            cursor = ''
        path = '/api/external/orders/v1/list'
        base_url = wms_attrs.get('base_url')
        url = f'{base_url}{path}'
        body = {
            "cursor": "",
            "subscribe": True
        }
        while True:
            start = datetime.now()
            body.update({'cursor': cursor})
            req_start = datetime.now()
            responce = requests.post(url, json=body, headers=headers)
            req_finish = datetime.now()
            req_time = req_finish - req_start
            print(f'wms order_responce: {responce.status_code} | req_time: {req_time.seconds}.{req_time.microseconds} sec')
            if not responce.status_code == 200:
                ValueError(_('ERROR'))

            orders = responce.json()['orders']
            cursor = responce.json()['cursor']

            if not orders:
                break
            for o in orders:
                if o['status'] == 'complete' and o['estatus'] == 'done' \
                        and o['type'] == 'acceptance':
                    order_status = self._create_or_update_purchace_order(o)
                    if not order_status:
                        continue
                elif o['status'] == 'complete' and o['estatus'] == 'done' \
                        and o['type'] in ['stowage', 'sale_stowage']:
                    order_status = self._stowage_update(o)
                    if not order_status:
                        continue
            wms.update_order_cursor(cursor)
            if len(orders) < 100:
                self.env.cr.commit()
                break
            self.env.cr.commit()
            finish = datetime.now()
            result = finish - start
            print(f'commited pack time: {result.seconds}.{result.microseconds} sec')
        wms.update_order_cursor(cursor)

