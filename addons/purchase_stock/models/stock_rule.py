# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare

from odoo import api, fields, models, SUPERUSER_ID, _, Command
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.tools import groupby


class StockRule(models.Model):
    _inherit = 'stock.rule'

    action = fields.Selection(selection_add=[
        ('buy', 'Buy')
    ], ondelete={'buy': 'cascade'})

    def _get_message_dict(self):
        message_dict = super(StockRule, self)._get_message_dict()
        __, destination, __, __ = self._get_message_values()
        message_dict.update({
            'buy': _('When products are needed in <b>%s</b>, <br/> '
                     'a request for quotation is created to fulfill the need.<br/>'
                     'Note: This rule will be used in combination with the rules<br/>'
                     'of the reception route(s)', destination)
        })
        return message_dict

    @api.depends('action')
    def _compute_picking_type_code_domain(self):
        remaining = self.browse()
        for rule in self:
            if rule.action == 'buy':
                rule.picking_type_code_domain = 'incoming'
            else:
                remaining |= rule
        super(StockRule, remaining)._compute_picking_type_code_domain()

    @api.onchange('action')
    def _onchange_action(self):
        if self.action == 'buy':
            self.location_src_id = False

    def _prepare_buy(self, procurement, taken_qties):
        # Get the schedule date in order to find a valid seller
        procurement_date_planned = fields.Datetime.from_string(procurement.values['date_planned'])

        if procurement.values.get('supplierinfo_id'):
            supplier = procurement.values['supplierinfo_id']
        elif procurement.values.get('orderpoint_id') and procurement.values['orderpoint_id'].supplier_id:
            supplier = procurement.values['orderpoint_id'].supplier_id
        else:
            supplier = procurement.product_id.with_company(procurement.company_id.id)._select_seller(
                partner_id=procurement.values.get("supplierinfo_name") or (
                            procurement.values.get("group_id") and procurement.values.get("group_id").partner_id),
                quantity=procurement.product_qty,
                date=max(procurement_date_planned.date(), fields.Date.today()),
                uom_id=procurement.product_uom)

        # Fall back on a supplier for which no price may be defined. Not ideal, but better than blocking the user.
        supplier = supplier or procurement.product_id._prepare_sellers(False).filtered(
            lambda s: not s.company_id or s.company_id == procurement.company_id
        )[:1]

        if not supplier:
            msg = _(
                'There is no matching vendor price to generate the purchase order for product %s (no vendor defined, minimum quantity not reached, dates not valid, ...). Go on the product form and complete the list of vendors.',
                procurement.product_id.display_name)
            raise ProcurementException([(procurement, msg)])

        partner = supplier.partner_id
        # we put `supplier_info` in values for extensibility purposes
        procurement.values['supplier'] = supplier
        procurement.values['propagate_cancel'] = self.propagate_cancel
        domain = self._make_po_get_domain(procurement.company_id, procurement.values, partner)

        # Check if a PO exists for the current domain.
        po = self.env['purchase.order'].sudo().search(list(domain), limit=1)
        if not po:
            if float_compare(procurement.product_qty, 0.0, precision_rounding=procurement.product_uom.rounding) >= 0:
                # We need a rule to generate the PO. However the rule generated
                # the same domain for PO and the _prepare_purchase_order method
                # should only uses the common rules's fields.
                po_vals = self._prepare_purchase_order(procurement.company_id, [procurement.origin], [procurement.values])
            else:
                return 'buy', {}
        else:
            po_vals = {'po_id': po.id}
            # If a purchase order is found, adapt its `origin` field.
            if po.origin:
                if procurement.origin not in po.origin.split(', '):
                    po_vals['origin'] = po.origin + ', ' + procurement.origin
            else:
                po_vals['origin'] = procurement.origin

        po_lines_by_product = {}
        grouped_po_lines = groupby(
            po.order_line.filtered(lambda l: not l.display_type and l.product_uom == l.product_id.uom_po_id),
            key=lambda l: l.product_id.id)
        for product, po_lines in grouped_po_lines:
            po_lines_by_product[product] = self.env['purchase.order.line'].concat(*po_lines)
        po_lines = po_lines_by_product.get(procurement.product_id.id, self.env['purchase.order.line'])
        po_line = po_lines._find_candidate(*procurement)
        if po_line:
            # If the procurement can be merge in an existing line. Directly write the new values on it
            po_vals['update_line'] = self._update_purchase_order_line(
                procurement.product_id, procurement.product_qty, procurement.product_uom, procurement.company_id, procurement.values, po_line
            )
            po_vals['update_line']['pol_id'] = po_line.id
        else:
            if float_compare(procurement.product_qty, 0, precision_rounding=procurement.product_uom.rounding) <= 0:
                # If procurement contains negative quantity, don't create a new line that would contain negative qty
                return 'buy', {}
            # If it does not exist a PO line for current procurement.
            # Generate the create values for it and add it to a list in order to create it in batch.
            po_vals['order_line'] = [Command.create(
                self.env['purchase.order.line']._prepare_purchase_order_line_from_procurement(*procurement, po or po_vals)
            )]
            # Check if we need to advance the order date for the new line
            order_date_planned = procurement.values['date_planned'] - relativedelta(days=procurement.values['supplier'].delay)
            po_date_order = po.date_order if po else po_vals.get('date_order', fields.Datetime.now)
            if fields.Date.to_date(order_date_planned) < fields.Date.to_date(po_date_order):
                if po:
                    po.date_planned = order_date_planned
                else:
                    po_vals['date_order'] = order_date_planned
        return 'buy', po_vals

    @api.model
    def _run_buy(self, po_vals, procurements):
        for po in po_vals:
            if 'po_id' in po:
                po_to_edit = self.env['purchase.order'].browse(po['po_id'])
                del po['po_id']
                update_line = False
                if po.get('update_line', False):
                    update_line = po['update_line']
                    del po['update_line']
                po_to_edit.sudo().write(po)
                if update_line:
                    po_line = self.env['purchase.order.line'].browse(update_line['pol_id'])
                    del update_line['pol_id']
                    po_line.sudo().write(update_line)
                self._confirm_new_moves(po_to_edit.order_line.move_dest_ids, procurements)
            else:
                created_po = self.env['purchase.order'].with_company(po['company_id']).with_user(SUPERUSER_ID).create(po)
                self._confirm_new_moves(created_po.order_line.move_dest_ids, procurements)

    def _get_lead_days(self, product, **values):
        """Add the company security lead time and the supplier delay to the cumulative delay
        and cumulative description. The company lead time is always displayed for onboarding
        purpose in order to indicate that those options are available.
        """
        delays, delay_description = super()._get_lead_days(product, **values)
        bypass_delay_description = self.env.context.get('bypass_delay_description')
        buy_rule = self.filtered(lambda r: r.action == 'buy')
        seller = 'supplierinfo' in values and values['supplierinfo'] or product.with_company(buy_rule.company_id)._select_seller(quantity=None)
        if not buy_rule or not seller:
            return delays, delay_description
        buy_rule.ensure_one()
        if not self.env.context.get('ignore_vendor_lead_time'):
            supplier_delay = seller[0].delay
            delays['total_delay'] += supplier_delay
            delays['purchase_delay'] += supplier_delay
            if not bypass_delay_description:
                delay_description.append((_('Vendor Lead Time'), _('+ %d day(s)', supplier_delay)))
        security_delay = buy_rule.picking_type_id.company_id.po_lead
        delays['total_delay'] += security_delay
        delays['security_lead_days'] += security_delay
        if not bypass_delay_description:
            delay_description.append((_('Purchase Security Lead Time'), _('+ %d day(s)', security_delay)))
        days_to_order = buy_rule.company_id.days_to_purchase
        delays['total_delay'] += days_to_order
        if not bypass_delay_description:
            delay_description.append((_('Days to Purchase'), _('+ %d day(s)', days_to_order)))
        return delays, delay_description

    @api.model
    def _get_procurements_to_merge_groupby(self, procurement):
        # Do not group procument from different orderpoint. 1. _quantity_in_progress
        # directly depends from the orderpoint_id on the line. 2. The stock move
        # generated from the order line has the orderpoint's location as
        # destination location. In case of move_dest_ids those two points are not
        # necessary anymore since those values are taken from destination moves.
        return procurement.product_id, procurement.product_uom, procurement.values['propagate_cancel'],\
            procurement.values.get('product_description_variants'),\
            (procurement.values.get('orderpoint_id') and not procurement.values.get('move_dest_ids')) and procurement.values['orderpoint_id']

    @api.model
    def _get_procurements_to_merge(self, procurements):
        """ Get a list of procurements values and create groups of procurements
        that would use the same purchase order line.
        params procurements_list list: procurements requests (not ordered nor
        sorted).
        return list: procurements requests grouped by their product_id.
        """
        return [pro_g for __, pro_g in groupby(procurements, key=self._get_procurements_to_merge_groupby)]

    @api.model
    def _merge_procurements(self, procurements_to_merge):
        """ Merge the quantity for procurements requests that could use the same
        order line.
        params similar_procurements list: list of procurements that have been
        marked as 'alike' from _get_procurements_to_merge method.
        return a list of procurements values where values of similar_procurements
        list have been merged.
        """
        merged_procurements = []
        for procurements in procurements_to_merge:
            quantity = 0
            move_dest_ids = self.env['stock.move']
            orderpoint_id = self.env['stock.warehouse.orderpoint']
            for procurement in procurements:
                if procurement.values.get('move_dest_ids'):
                    move_dest_ids |= procurement.values['move_dest_ids']
                if not orderpoint_id and procurement.values.get('orderpoint_id'):
                    orderpoint_id = procurement.values['orderpoint_id']
                quantity += procurement.product_qty
            # The merged procurement can be build from an arbitrary procurement
            # since they were mark as similar before. Only the quantity and
            # some keys in values are updated.
            values = dict(procurement.values)
            values.update({
                'move_dest_ids': move_dest_ids,
                'orderpoint_id': orderpoint_id,
            })
            merged_procurement = self.env['procurement.group'].Procurement(
                procurement.product_id, quantity, procurement.product_uom,
                procurement.location_id, procurement.name, procurement.origin,
                procurement.company_id, values
            )
            merged_procurements.append(merged_procurement)
        return merged_procurements

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        partner = values['supplier'].partner_id
        procurement_uom_po_qty = product_uom._compute_quantity(product_qty, product_id.uom_po_id, rounding_method='HALF-UP')
        seller = product_id.with_company(company_id)._select_seller(
            partner_id=partner,
            quantity=line.product_qty + procurement_uom_po_qty,
            date=line.order_id.date_order and line.order_id.date_order.date(),
            uom_id=product_id.uom_po_id)

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, line.product_id.supplier_taxes_id, line.taxes_id, company_id) if seller else 0.0
        if price_unit and seller and line.order_id.currency_id and seller.currency_id != line.order_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, line.order_id.currency_id, line.order_id.company_id, fields.Date.today())

        res = {
            'product_qty': line.product_qty + procurement_uom_po_qty,
            'price_unit': price_unit,
            'move_dest_ids': values.get('move_dest_ids', [])
        }
        orderpoint_id = values.get('orderpoint_id')
        if orderpoint_id:
            res['orderpoint_id'] = orderpoint_id.id
        return res

    def _prepare_purchase_order(self, company_id, origins, values):
        """ Create a purchase order for procuremets that share the same domain
        returned by _make_po_get_domain.
        params values: values of procurements
        params origins: procuremets origins to write on the PO
        """
        purchase_date = min([value.get('date_order') or fields.Datetime.from_string(value['date_planned']) - relativedelta(days=int(value['supplier'].delay)) for value in values])

        # Since the procurements are grouped if they share the same domain for
        # PO but the PO does not exist. In this case it will create the PO from
        # the common procurements values. The common values are taken from an
        # arbitrary procurement. In this case the first.
        values = values[0]
        partner = values['supplier'].partner_id

        fpos = self.env['account.fiscal.position'].with_company(company_id)._get_fiscal_position(partner)

        gpo = self.group_propagation_option
        group = (gpo == 'fixed' and self.group_id.id) or \
                (gpo == 'propagate' and values.get('group_id') and values['group_id'].id) or False

        return {
            'partner_id': partner.id,
            'user_id': partner.buyer_id.id,
            'picking_type_id': self.picking_type_id.id,
            'company_id': company_id.id,
            'currency_id': partner.with_company(company_id).property_purchase_currency_id.id or company_id.currency_id.id,
            'dest_address_id': values.get('partner_id', False),
            'origin': ', '.join(origins),
            'payment_term_id': partner.with_company(company_id).property_supplier_payment_term_id.id,
            'date_order': purchase_date,
            'fiscal_position_id': fpos.id,
            'group_id': group
        }

    def _make_po_get_domain(self, company_id, values, partner):
        gpo = self.group_propagation_option
        group = (gpo == 'fixed' and self.group_id) or \
                (gpo == 'propagate' and 'group_id' in values and values['group_id']) or False

        domain = (
            ('partner_id', '=', partner.id),
            ('state', '=', 'draft'),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('company_id', '=', company_id.id),
            ('user_id', '=', partner.buyer_id.id),
        )
        delta_days = self.env['ir.config_parameter'].sudo().get_param('purchase_stock.delta_days_merge')
        if values.get('orderpoint_id') and delta_days is not False:
            procurement_date = fields.Date.to_date(values['date_planned']) - relativedelta(days=int(values['supplier'].delay))
            delta_days = int(delta_days)
            domain += (
                ('date_order', '<=', datetime.combine(procurement_date + relativedelta(days=delta_days), datetime.max.time())),
                ('date_order', '>=', datetime.combine(procurement_date - relativedelta(days=delta_days), datetime.min.time()))
            )
        if group:
            domain += (('group_id', '=', group.id),)
        return domain

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        res = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        res['purchase_line_id'] = None
        if self.location_dest_id.usage == "supplier":
            res['purchase_line_id'], res['partner_id'] = move_to_copy._get_purchase_line_and_partner_from_chain()
        return res
