# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
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
        super()._compute_picking_type_code_domain()
        for rule in self:
            if rule.action == 'buy':
                rule.picking_type_code_domain = rule.picking_type_code_domain or [] + ['incoming']

    @api.onchange('action')
    def _onchange_action(self):
        if self.action == 'buy':
            self.location_src_id = False

    @api.model
    def run(self, procurements, raise_user_error=True):
        wh_by_comp = dict()
        for procurement in procurements:
            routes = procurement.values.get('route_ids')
            if routes and any(r.action == 'buy' for r in routes.rule_ids):
                company = procurement.company_id
                if company not in wh_by_comp:
                    wh_by_comp[company] = self.env['stock.warehouse'].search([('company_id', '=', company.id)])
                wh = wh_by_comp[company]
                procurement.values['route_ids'] |= wh.reception_route_id
        return super().run(procurements, raise_user_error=raise_user_error)

    @api.model
    def _run_buy(self, procurements):
        procurements_by_po_domain = defaultdict(list)
        errors = []
        for procurement, rule in procurements:
            company_id = rule.company_id or procurement.company_id

            supplier = self._find_procurement_supplier(company_id, procurement)
            # procurement_partner context key used to set a partner without a pricelist as supplier
            procurement_partner = procurement.values.get('procurement_partner') or supplier.partner_id

            if not supplier and self.env.context.get('from_orderpoint'):
                msg = _('There is no matching vendor price to generate the purchase order for product %s (no vendor defined, minimum quantity not reached, dates not valid, ...). Go on the product form and complete the list of vendors.', procurement.product_id.display_name)
                errors.append((procurement, msg))
            elif not (supplier or procurement_partner):
                # If no supplier or procurement_partner, we cannot create a PO, but don't want to block SO
                moves = procurement.values.get('move_dest_ids') or self.env['stock.move']
                if moves.propagate_cancel:
                    moves._action_cancel()
                moves.procure_method = 'make_to_stock'
                self._notify_responsible(procurement)
                continue

            procurement.values['supplier'] = supplier  # Can be None (in which case we use fallbacks for currency, delays ...)
            procurement.values['procurement_partner'] = procurement_partner  # Cannot be None
            procurement.values['propagate_cancel'] = rule.propagate_cancel

            domain = rule._make_po_get_domain(company_id, procurement.values, procurement_partner)
            procurements_by_po_domain[domain].append((procurement, rule))

        if errors:
            raise ProcurementException(errors)

        for domain, procurements_rules in procurements_by_po_domain.items():
            # Get the procurements for the current domain.
            # Get the rules for the current domain. Their only use is to create
            # the PO if it does not exist.
            procurements, rules = zip(*procurements_rules)

            # Get the set of procurement origin for the current domain.
            origins = set([p.origin for p in procurements if p.origin])
            # Check if a PO exists for the current domain.
            po = self.env['purchase.order'].sudo().search([dom for dom in domain], limit=1)
            company_id = rules[0].company_id or procurements[0].company_id
            if not po:
                positive_values = [p.values for p in procurements if p.product_uom.compare(p.product_qty, 0.0) >= 0]
                if positive_values:
                    # We need a rule to generate the PO. However the rule generated
                    # the same domain for PO and the _prepare_purchase_order method
                    # should only uses the common rules's fields.
                    vals = rules[0]._prepare_purchase_order(company_id, origins, positive_values)
                    # The company_id is the same for all procurements since
                    # _make_po_get_domain add the company in the domain.
                    # We use SUPERUSER_ID since we don't want the current user to be follower of the PO.
                    # Indeed, the current user may be a user without access to Purchase, or even be a portal user.
                    po = self.env['purchase.order'].with_company(company_id).with_user(SUPERUSER_ID).create(vals)
            else:
                reference_ids = set()
                for procurement in procurements:
                    reference_ids |= set(procurement.values.get('reference_ids', self.env['stock.reference']).ids)
                # If a purchase order is found, adapt its `origin` field.
                po.reference_ids = [Command.link(ref_id) for ref_id in reference_ids]
                if po.origin:
                    missing_origins = origins - set(po.origin.split(', '))
                    if missing_origins:
                        po.write({'origin': po.origin + ', ' + ', '.join(missing_origins)})
                else:
                    po.write({'origin': ', '.join(origins)})

            procurements_to_merge = self._get_procurements_to_merge(procurements)
            procurements = self._merge_procurements(procurements_to_merge)

            po_lines_by_product = {}
            grouped_po_lines = groupby(po.order_line.filtered(lambda l: not l.display_type), key=lambda l: l.product_id.id)
            for product, po_lines in grouped_po_lines:
                po_lines_by_product[product] = self.env['purchase.order.line'].concat(*po_lines)
            po_line_values = []
            for procurement in procurements:
                po_lines = po_lines_by_product.get(procurement.product_id.id, self.env['purchase.order.line'])
                po_line = po_lines._find_candidate(*procurement)

                if po_line:
                    # If the procurement can be merge in an existing line. Directly
                    # write the new values on it.
                    vals = self._update_purchase_order_line(procurement.product_id,
                        procurement.product_qty, procurement.product_uom, company_id,
                        procurement.values, po_line)
                    po_line.sudo().write(vals)
                else:
                    if procurement.product_uom.compare(procurement.product_qty, 0) <= 0:
                        # If procurement contains negative quantity, don't create a new line that would contain negative qty
                        continue
                    # If it does not exist a PO line for current procurement.
                    # Generate the create values for it and add it to a list in
                    # order to create it in batch.
                    po_line_values.append(self.env['purchase.order.line']._prepare_purchase_order_line_from_procurement(
                        *procurement, po))
                    # Check if we need to advance the order date for the new line
                    delay = (supplier and supplier.delay) or 0
                    date_planned = po.date_planned or min(v['date_planned'] for v in po_line_values)
                    order_date_planned = date_planned - relativedelta(days=delay)
                    if fields.Date.to_date(order_date_planned) < fields.Date.to_date(po.date_order):
                        po.date_order = order_date_planned

            self.env['purchase.order.line'].sudo().create(po_line_values)

    def _filter_warehouse_routes(self, product, warehouses, route):
        if any(rule.action == 'buy' for rule in route.rule_ids):
            if product.seller_ids:
                return super()._filter_warehouse_routes(product, warehouses, route)
            return False
        return super()._filter_warehouse_routes(product, warehouses, route)

    def _post_vendor_notification(self, records_to_notify, users_to_notify, product):
        notification_msg = Markup(" ").join(Markup("%s") % user._get_html_link(f'@{user.name}') for user in users_to_notify)
        notification_msg += Markup("<br/>%s <strong>%s</strong>, %s") % (_("No supplier has been found to replenish"), product.display_name, _("this product should be manually replenished."))
        records_to_notify.message_post(body=notification_msg, partner_ids=users_to_notify.ids)

    def _notify_responsible(self, procurement):
        pass  # Override in sale_purchase_stock and purchase_mrp to notify salesperson or MO responsible

    def _get_lead_days(self, product, **values):
        """Add the supplier delay to the cumulative delay and cumulative description.
        """
        delays, delay_description = super()._get_lead_days(product, **values)
        bypass_delay_description = self.env.context.get('bypass_delay_description')
        buy_rule = self.filtered(lambda r: r.action == 'buy')
        seller = 'supplierinfo' in values and values['supplierinfo'] or product.with_company(buy_rule.company_id)._select_seller(quantity=None)
        if not buy_rule:
            return delays, delay_description
        if not seller:
            delays['total_delay'] += 365
            delays['no_vendor_found_delay'] += 365
            if not bypass_delay_description:
                delay_description.append((_('No Vendor Found'), _('+ %s day(s)', 365)))
            return delays, delay_description
        buy_rule.ensure_one()
        if not self.env.context.get('ignore_vendor_lead_time'):
            supplier_delay = seller[:1].delay
            delays['total_delay'] += supplier_delay
            delays['purchase_delay'] += supplier_delay
            if not bypass_delay_description:
                delay_description.append((_('Receipt Date'), supplier_delay))
                delay_description.append((_('Vendor Lead Time'), _('+ %d day(s)', supplier_delay)))
        days_to_order = buy_rule.company_id.days_to_purchase
        delays['total_delay'] += days_to_order
        if not bypass_delay_description:
            delay_description.append((_('Order Deadline'), days_to_order))
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
            merged_procurement = self.env['stock.rule'].Procurement(
                procurement.product_id, quantity, procurement.product_uom,
                procurement.location_id, procurement.name, procurement.origin,
                procurement.company_id, values
            )
            merged_procurements.append(merged_procurement)
        return merged_procurements

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, company_id, values, line):
        procurement_uom_po_qty = product_uom._compute_quantity(product_qty, line.product_uom_id, rounding_method='HALF-UP')
        seller = product_id.with_company(company_id)._select_seller(
            partner_id=line.selected_seller_id.partner_id or line.partner_id,
            quantity=line.product_qty + procurement_uom_po_qty,
            date=line.order_id.date_order and line.order_id.date_order.date(),
            uom_id=line.product_uom_id,
            params={'force_uom': values.get('force_uom')})

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, line.product_id.supplier_taxes_id, line.sudo().tax_ids, company_id) if seller else 0.0
        if price_unit and seller and line.order_id.currency_id and seller.currency_id != line.order_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, line.order_id.currency_id, line.order_id.company_id, fields.Date.today())

        res = {
            'product_qty': line.product_qty + procurement_uom_po_qty,
            'price_unit': price_unit,
            'move_dest_ids': [(4, x.id) for x in values.get('move_dest_ids', [])]
        }
        if seller.product_uom_id != line.product_uom_id and not values.get('force_uom'):
            res['product_qty'] = line.product_uom_id._compute_quantity(res['product_qty'], seller.product_uom_id, rounding_method='HALF-UP')
            res['product_uom_id'] = seller.product_uom_id
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
        partner = values['procurement_partner']
        currency_id = values['supplier'].currency_id.id if values['supplier'] else None

        fpos = self.env['account.fiscal.position'].with_company(company_id)._get_fiscal_position(partner)

        return {
            'partner_id': partner.id,
            'user_id': partner.buyer_id.id,
            'picking_type_id': self.picking_type_id.id,
            'company_id': company_id.id,
            'currency_id': currency_id or partner.with_company(company_id).property_purchase_currency_id.id or company_id.currency_id.id,
            'dest_address_id': values.get('partner_id', False),
            'origin': ', '.join(origins),
            'payment_term_id': partner.with_company(company_id).property_supplier_payment_term_id.id,
            'date_order': purchase_date,
            'fiscal_position_id': fpos.id,
            'reference_ids': [Command.set(values.get('reference_ids', self.env['stock.reference']).ids)],
        }

    def _make_po_get_domain(self, company_id, values, partner):
        currency = ('supplier' in values and values['supplier'].currency_id) or \
                   partner.with_company(company_id).property_purchase_currency_id or \
                   company_id.currency_id
        domain = (
            ('partner_id', '=', partner.id),
            ('state', '=', 'draft'),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('company_id', '=', company_id.id),
            ('user_id', '=', partner.buyer_id.id),
            ('currency_id', '=', currency.id),
        )
        if partner.group_rfq == 'default':
            if values.get('reference_ids'):
                domain += (('reference_ids', 'in', tuple(values['reference_ids'].ids)),)
        date_planned = fields.Datetime.from_string(values['date_planned'])
        if partner.group_rfq == 'day':
            start_dt = datetime.combine(date_planned, datetime.min.time())
            end_dt = datetime.combine(date_planned, datetime.max.time())
            domain += (('date_planned', '>=', start_dt), ('date_planned', '<=', end_dt))
        if partner.group_rfq == 'week':
            if partner.group_on == 'default':
                start_dt = datetime.combine(date_planned - relativedelta(days=date_planned.isoweekday()), datetime.min.time())
                end_dt = datetime.combine(date_planned + relativedelta(days=6 - date_planned.isoweekday()), datetime.max.time())
                domain += (('date_planned', '>=', start_dt), ('date_planned', '<=', end_dt))
            else:
                delta_days = (7 + int(partner.group_on) - date_planned.isoweekday()) % 7
                date = date_planned + relativedelta(days=delta_days)
                start_dt = datetime.combine(date, datetime.min.time())
                end_dt = datetime.combine(date, datetime.max.time())
                domain += (('date_planned', '>=', start_dt), ('date_planned', '<=', end_dt))

        return domain

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        res = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        res['purchase_line_id'] = None
        if self.location_dest_id.usage == "supplier":
            res['purchase_line_id'], res['partner_id'] = move_to_copy._get_purchase_line_and_partner_from_chain()
        return res

    def _find_procurement_supplier(self, company, procurement):
        """ Finds the partner to attach the PO to (ie. at PO level not line level)
            :return: Supplier of best matching pricelist for procurement values,
            dropping constraints progressively, None if no supplier found (eg. no pricelist at all).
            :rtype: product.supplierinfo | None
        """
        supplier = False
        if procurement.values.get('supplierinfo_id'):
            supplier = procurement.values['supplierinfo_id']
        elif procurement.values.get('orderpoint_id') and procurement.values['orderpoint_id'].supplier_id:
            supplier = procurement.values['orderpoint_id'].supplier_id
        else:
            procurement_date_planned = fields.Datetime.from_string(procurement.values['date_planned'])
            supplier = self._pick_supplier(
                company,
                procurement.product_id,
                partner=procurement.values.get('procurement_partner'),
                qty=procurement.product_qty,
                uom=procurement.product_uom,
                date=max(procurement_date_planned.date(), fields.Date.today()),
                params={"force_uom": procurement.values.get('force_uom')},
            )

        return supplier

    def _pick_supplier(self, company, product, partner=False, qty=None, uom=False, date=None, params=False):
        """ Flex find best pricelist for a defined product and company
            dropping constraints (eg. min_qty, uom...) progressively.

            :param partner: False to select the best pricelist regardless of partner.
            :return: best matching pricelist.
            :rtype: product.supplierinfo
        """
        p = product.with_company(company)
        supplier = p._select_seller(partner_id=partner, quantity=qty, date=date, uom_id=uom, params=params) or \
                   p._select_seller(partner_id=partner, quantity=None, date=date, uom_id=uom, params=params) or \
                   p._select_seller(partner_id=partner, quantity=None, uom_id=uom, params=params) or \
                   p._select_seller(partner_id=partner, quantity=None, params=params) or \
                   p._select_seller(partner_id=partner, quantity=None)

        if not supplier and not partner:  # Last fallback, also matching expired pricelists
            supplier = p._select_seller(quantity=None) or p._prepare_sellers()[:1]
        return supplier


class StockRoute(models.Model):
    _inherit = "stock.route"

    def _is_valid_resupply_route_for_product(self, product):
        if any(rule.action == 'buy' for rule in self.rule_ids):
            return bool(product.seller_ids)
        return super()._is_valid_resupply_route_for_product(product)
