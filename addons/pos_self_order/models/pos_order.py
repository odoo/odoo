# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Dict

from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    combo_parent_id = fields.Many2one('pos.order.line', string='Combo Parent')
    combo_line_ids = fields.One2many('pos.order.line', 'combo_parent_id', string='Combo Lines')
    combo_id = fields.Many2one('pos.combo', string='Combo line reference')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (vals.get('combo_parent_uuid')):
                vals.update([
                    ('combo_parent_id', self.search([('uuid', '=', vals.get('combo_parent_uuid'))]).id)
                ])
            if 'combo_parent_uuid' in vals:
                del vals['combo_parent_uuid']
        return super().create(vals_list)

    def write(self, vals):
        if (vals.get('combo_parent_uuid')):
            vals.update([
                ('combo_parent_id', self.search([('uuid', '=', vals.get('combo_parent_uuid'))]).id)
            ])
        if 'combo_parent_uuid' in vals:
            del vals['combo_parent_uuid']
        return super().write(vals)

class PosOrder(models.Model):
    _inherit = "pos.order"

    table_stand_number = fields.Char(string="Table Stand Number")

    def _compute_tax_details(self):
        self.ensure_one()
        taxes = sum([line.tax_ids.with_company(self.company_id).compute_all(line.price_unit, quantity=line.qty, product=line.product_id)['taxes']
               for line in self.lines], [])
        tax_percetanges = {tax['id']: tax['amount'] for tax in self.env['account.tax'].search([]).read(['amount'])}
        merged_tax_details = {}
        for tax_obj in taxes:
            tax_id = tax_obj['id']
            if tax_id not in merged_tax_details:
                merged_tax_details[tax_id] = {
                    'tax': {
                        'id': tax_id,
                        'amount': tax_percetanges[tax_id]
                    },
                    'name': tax_obj['name'],
                    'amount': 0.0,
                    'base': 0.0,
                }
            merged_tax_details[tax_id]['amount'] += tax_obj['amount']
            merged_tax_details[tax_id]['base'] += tax_obj['base']
        return list(merged_tax_details.values())

    @api.model
    def sync_from_ui(self, orders):
        for order in orders:
            if order.get('id'):
                order_id = order['id']

                if isinstance(order_id, int):
                    old_order = self.env['pos.order'].browse(order_id)
                    if old_order.takeaway:
                        order['takeaway'] = old_order.takeaway

        return super().sync_from_ui(orders)

    def _process_saved_order(self, draft):
        res = super()._process_saved_order(draft)

        if self.env.context.get('from_self') is not True:
            self._send_notification(self)

        return res

    @api.model
    def remove_from_ui(self, server_ids):
        order_ids = self.env['pos.order'].browse(server_ids)
        order_ids.state = 'cancel'
        self._send_notification(order_ids)

        return super().remove_from_ui(server_ids)

    def _send_notification(self, order_ids):
        for order in order_ids:
            if order.access_token and order.state != 'draft':
                order._notify('ORDER_STATE_CHANGED', {
                    'access_token': order.access_token,
                    'state': order.state
                })
            else:
                order._notify('ORDER_CHANGED', {
                    'order': order._export_for_self_order()
                })

    def _export_for_self_order(self) -> Dict:
        self.ensure_one()

        return {
            "id": self.id,
            "pos_config_id": self.config_id.id,
            "takeaway": self.takeaway,
            "pos_reference": self.pos_reference,
            "access_token": self.access_token,
            "table_stand_number": self.table_stand_number,
            "state": self.state,
            "date_order": str(self.date_order),
            "amount_total": self.amount_total,
            "amount_tax": self.amount_tax,
            "lines": [
                {
                    "id": line.id,
                    "price_subtotal": line.price_subtotal,
                    "price_subtotal_incl": line.price_subtotal_incl,
                    "product_id": line.product_id.id,
                    "attribute_value_ids": line.attribute_value_ids.ids,
                    "custom_attribute_value_ids": line.custom_attribute_value_ids.read(['id', 'name', 'custom_product_template_attribute_value_id', 'custom_value'], load=False),
                    "uuid": line.uuid,
                    "qty": line.qty,
                    "customer_note": line.customer_note,
                    "full_product_name": line.full_product_name,
                }
                for line in self.lines
            ],
            "payment_lines": [{
                "name": payment.payment_method_id.name,
                "amount": payment.amount
            } for payment in self.payment_ids],
            "tax_details": self._compute_tax_details(),
        }

    @api.model
    def get_standalone_self_order(self):
        orders = self.env['pos.order'].search_read([
            *self.env["pos.order"]._check_company_domain(self.env.company),
            ('state', '=', 'draft'),
            '|', ('pos_reference', 'ilike', 'Kiosk'),
            ('pos_reference', 'ilike', 'Self-Order'),
            ('table_id', '=', False),
        ], [], load=False)
        return {'pos.order': orders}
