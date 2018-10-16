# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError


class StockRule(models.Model):
    _inherit = 'stock.rule'

    action = fields.Selection(selection_add=[('buy', 'Buy')])

    def _get_message_dict(self):
        message_dict = super(StockRule, self)._get_message_dict()
        dummy, destination, dummy = self._get_message_values()
        message_dict.update({
            'buy': _('When products are needed in <b>%s</b>, <br/> a request for quotation is created to fulfill the need.') % (destination)
        })
        return message_dict

    @api.onchange('action')
    def _onchange_action(self):
        domain = {'picking_type_id': []}
        if self.action == 'buy':
            self.location_src_id = False
            domain = {'picking_type_id': [('code', '=', 'incoming')]}
        return {'domain': domain}

    @api.multi
    def _run_buy(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        cache = {}
        suppliers = product_id.seller_ids\
            .filtered(lambda r: (not r.company_id or r.company_id == values['company_id']) and (not r.product_id or r.product_id == product_id))
        if not suppliers:
            msg = _('There is no vendor associated to the product %s. Please define a vendor for this product.') % (product_id.display_name,)
            raise UserError(msg)   
        supplier = self._make_po_select_supplier(values, suppliers)
        partner = supplier.name
        # we put `supplier_info` in values for extensibility purposes
        values['supplier'] = supplier

        domain = self._make_po_get_domain(values, partner)
        if domain in cache:
            po = cache[domain]
        else:
            po = self.env['purchase.order'].sudo().search([dom for dom in domain])
            po = po[0] if po else False
            cache[domain] = po
        if not po:
            vals = self._prepare_purchase_order(product_id, product_qty, product_uom, origin, values, partner)
            company_id = values.get('company_id') and values['company_id'].id or self.env.user.company_id.id
            po = self.env['purchase.order'].with_context(force_company=company_id).sudo().create(vals)
            cache[domain] = po
        elif not po.origin or origin not in po.origin.split(', '):
            if po.origin:
                if origin:
                    po.write({'origin': po.origin + ', ' + origin})
                else:
                    po.write({'origin': po.origin})
            else:
                po.write({'origin': origin})

        # Create Line
        po_line = False
        for line in po.order_line:
            if line.product_id == product_id and line.product_uom == product_id.uom_po_id:
                if line._merge_in_existing_line(product_id, product_qty, product_uom, location_id, name, origin, values):
                    vals = self._update_purchase_order_line(product_id, product_qty, product_uom, values, line, partner)
                    po_line = line.write(vals)
                    break
        if not po_line:
            vals = self._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, partner)
            self.env['purchase.order.line'].sudo().create(vals)

    def _get_purchase_schedule_date(self, values):
        """Return the datetime value to use as Schedule Date (``date_planned``) for the
           Purchase Order Lines created to satisfy the given procurement. """
        procurement_date_planned = fields.Datetime.from_string(values['date_planned'])
        schedule_date = (procurement_date_planned - relativedelta(days=values['company_id'].po_lead))
        return schedule_date

    def _get_purchase_order_date(self, product_id, product_qty, product_uom, values, partner, schedule_date):
        """Return the datetime value to use as Order Date (``date_order``) for the
           Purchase Order created to satisfy the given procurement. """
        seller = product_id._select_seller(
            partner_id=partner,
            quantity=product_qty,
            date=schedule_date and schedule_date.date(),
            uom_id=product_uom)

        return schedule_date - relativedelta(days=int(seller.delay))

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, values, line, partner):
        procurement_uom_po_qty = product_uom._compute_quantity(product_qty, product_id.uom_po_id)
        seller = product_id._select_seller(
            partner_id=partner,
            quantity=line.product_qty + procurement_uom_po_qty,
            date=line.order_id.date_order and line.order_id.date_order.date(),
            uom_id=product_id.uom_po_id)

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, line.product_id.supplier_taxes_id, line.taxes_id, values['company_id']) if seller else 0.0
        if price_unit and seller and line.order_id.currency_id and seller.currency_id != line.order_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, line.order_id.currency_id, line.order_id.company_id, fields.Date.today())

        return {
            'product_qty': line.product_qty + procurement_uom_po_qty,
            'price_unit': price_unit,
            'move_dest_ids': [(4, x.id) for x in values.get('move_dest_ids', [])]
        }

    @api.multi
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, partner):
        procurement_uom_po_qty = product_uom._compute_quantity(product_qty, product_id.uom_po_id)
        seller = product_id._select_seller(
            partner_id=partner,
            quantity=procurement_uom_po_qty,
            date=po.date_order and po.date_order.date(),
            uom_id=product_id.uom_po_id)

        taxes = product_id.supplier_taxes_id
        fpos = po.fiscal_position_id
        taxes_id = fpos.map_tax(taxes, product_id, seller.name) if fpos else taxes
        if taxes_id:
            taxes_id = taxes_id.filtered(lambda x: x.company_id.id == values['company_id'].id)

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, product_id.supplier_taxes_id, taxes_id, values['company_id']) if seller else 0.0
        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, po.currency_id, po.company_id, po.date_order or fields.Date.today())

        product_lang = product_id.with_context({
            'lang': partner.lang,
            'partner_id': partner.id,
        })
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        date_planned = self.env['purchase.order.line']._get_date_planned(seller, po=po).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        return {
            'name': name,
            'product_qty': procurement_uom_po_qty,
            'product_id': product_id.id,
            'product_uom': product_id.uom_po_id.id,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'orderpoint_id': values.get('orderpoint_id', False) and values.get('orderpoint_id').id,
            'taxes_id': [(6, 0, taxes_id.ids)],
            'order_id': po.id,
            'move_dest_ids': [(4, x.id) for x in values.get('move_dest_ids', [])],
        }

    def _prepare_purchase_order(self, product_id, product_qty, product_uom, origin, values, partner):
        schedule_date = self._get_purchase_schedule_date(values)
        purchase_date = self._get_purchase_order_date(product_id, product_qty, product_uom, values, partner, schedule_date)
        fpos = self.env['account.fiscal.position'].with_context(force_company=values['company_id'].id).get_fiscal_position(partner.id)

        gpo = self.group_propagation_option
        group = (gpo == 'fixed' and self.group_id.id) or \
                (gpo == 'propagate' and values.get('group_id') and values['group_id'].id) or False

        return {
            'partner_id': partner.id,
            'picking_type_id': self.picking_type_id.id,
            'company_id': values['company_id'].id,
            'currency_id': partner.with_context(force_company=values['company_id'].id).property_purchase_currency_id.id or self.env.user.company_id.currency_id.id,
            'dest_address_id': values.get('partner_id', False),
            'origin': origin,
            'payment_term_id': partner.with_context(force_company=values['company_id'].id).property_supplier_payment_term_id.id,
            'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'fiscal_position_id': fpos,
            'group_id': group
        }

    def _make_po_select_supplier(self, values, suppliers):
        """ Method intended to be overridden by customized modules to implement any logic in the
            selection of supplier.
        """
        return suppliers[0]

    def _make_po_get_domain(self, values, partner):
        domain = super(StockRule, self)._make_po_get_domain(values, partner)
        gpo = self.group_propagation_option
        group = (gpo == 'fixed' and self.group_id) or \
                (gpo == 'propagate' and 'group_id' in values and values['group_id']) or False

        domain += (
            ('partner_id', '=', partner.id),
            ('state', '=', 'draft'),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('company_id', '=', values['company_id'].id),
        )
        if group:
            domain += (('group_id', '=', group.id),)
        return domain

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        res = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        res['purchase_line_id'] = None
        return res
