# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Business Applications
#    Copyright (c) 2015 Odoo S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    carrier_price = fields.Float(string="Shipping Cost", readonly=True)
    delivery_type = fields.Selection(related='carrier_id.delivery_type', readonly=True)

    @api.multi
    def do_transfer(self):
        res = super(StockPicking, self).do_transfer()

        if self.carrier_id and self.carrier_id.delivery_type != 'grid':
            self.send_to_shipper()
        return res

    # Signature due to strange old api methods
    @api.model
    def _prepare_shipping_invoice_line(self, picking, invoice):
        picking.ensure_one()
        invoice.ensure_one()

        carrier = picking.carrier_id

        # No carrier
        if not carrier:
            return None
        # Carrier already invoiced on the sale order
        if any(inv_line.product_id.id == carrier.product_id.id for inv_line in invoice.invoice_line_ids):
            return None

        # Classic carrier
        if carrier.delivery_type == 'grid':
            return super(StockPicking, self)._prepare_shipping_invoice_line(picking, invoice)

        # Shipping provider
        price = picking.carrier_price

        account_id = carrier.product_id.property_account_income.id
        if not account_id:
            account_id = carrier.product_id.categ_id.property_account_income_categ.id

        taxes = carrier.product_id.taxes_id
        taxes_ids = taxes.ids

        # Apply original SO fiscal position
        if picking.sale_id.fiscal_position_id:
            fpos = picking.sale_id.fiscal_position_id
            account_id = fpos.map_account(account_id)
            taxes_ids = fpos.map_tax(taxes).ids

        res = {
            'name': carrier.name,
            'invoice_id': invoice.id,
            'uos_id': carrier.product_id.uos_id.id,
            'product_id': carrier.product_id.id,
            'account_id': account_id,
            'price_unit': price,
            'quantity': 1,
            'invoice_line_tax_ids': [(6, 0, taxes_ids)],
        }

        return res

    @api.one
    def send_to_shipper(self):
        res = self.carrier_id.send_shipping(self)[0]
        self.carrier_price = res['exact_price']
        self.carrier_tracking_ref = res['tracking_number']
        msg = "Shipment sent to carrier %s for expedition with tracking number %s" % (self.carrier_id.name, self.carrier_tracking_ref)
        self.message_post(body=msg)

    @api.multi
    def open_website_url(self):
        self.ensure_one()

        client_action = {'type': 'ir.actions.act_url',
                         'name': "Shipment Tracking Page",
                         'target': 'new',
                         'url': self.carrier_id.get_tracking_link(self)[0]
                         }
        return client_action

    @api.one
    def cancel_shipment(self):
        self.carrier_id.cancel_shipment(self)
        msg = "Shipment %s cancelled" % self.carrier_tracking_ref
        self.message_post(body=msg)
        self.carrier_tracking_ref = False
