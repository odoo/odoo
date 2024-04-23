# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.osv import expression
from odoo.tools import float_compare, OrderedSet


class StockRule(models.Model):
    _inherit = 'stock.rule'
    action = fields.Selection(selection_add=[
        ('manufacture', 'Manufacture')
    ], ondelete={'manufacture': 'cascade'})

    def _get_message_dict(self):
        message_dict = super(StockRule, self)._get_message_dict()
        source, destination, __ = self._get_message_values()
        manufacture_message = _('When products are needed in <b>%s</b>, <br/> a manufacturing order is created to fulfill the need.', destination)
        if self.location_src_id:
            manufacture_message += _(' <br/><br/> The components will be taken from <b>%s</b>.', source)
        message_dict['manufacture'] = manufacture_message
        return message_dict

    @api.depends('action')
    def _compute_picking_type_code_domain(self):
        remaining = self.browse()
        for rule in self:
            if rule.action == 'manufacture':
                rule.picking_type_code_domain = 'mrp_operation'
            else:
                remaining |= rule
        super(StockRule, remaining)._compute_picking_type_code_domain()

    def _should_auto_confirm_procurement_mo(self, p):
        return (not p.orderpoint_id and p.move_raw_ids) or (p.move_dest_ids.procure_method != 'make_to_order' and not p.move_raw_ids and not p.workorder_ids)

    @api.model
    def _run_manufacture(self, procurements):
        new_productions_values_by_company = defaultdict(list)
        for procurement, rule in procurements:
            if float_compare(procurement.product_qty, 0, precision_rounding=procurement.product_uom.rounding) <= 0:
                # If procurement contains negative quantity, don't create a MO that would be for a negative value.
                continue
            bom = rule._get_matching_bom(procurement.product_id, procurement.company_id, procurement.values)

            mo = self.env['mrp.production']
            mto_route = self.env['stock.warehouse']._find_global_route('stock.route_warehouse0_mto', _('Replenish on Order (MTO)'))
            if rule.route_id != mto_route and procurement.origin != 'MPS':
                gpo = rule.group_propagation_option
                group = (gpo == 'fixed' and rule.group_id) or \
                        (gpo == 'propagate' and 'group_id' in procurement.values and procurement.values['group_id']) or False
                domain = (
                    ('bom_id', '=', bom.id),
                    ('product_id', '=', procurement.product_id.id),
                    ('state', 'in', ['draft', 'confirmed']),
                    ('is_planned', '=', False),
                    ('picking_type_id', '=', rule.picking_type_id.id),
                    ('company_id', '=', procurement.company_id.id),
                    ('user_id', '=', False),
                )
                if procurement.values.get('orderpoint_id'):
                    procurement_date = datetime.combine(
                        fields.Date.to_date(procurement.values['date_planned']) - relativedelta(days=int(bom.produce_delay)),
                        datetime.max.time()
                    )
                    domain += ('|',
                               '&', ('state', '=', 'draft'), ('date_deadline', '<=', procurement_date),
                               '&', ('state', '=', 'confirmed'), ('date_start', '<=', procurement_date))
                if group:
                    domain += (('procurement_group_id', '=', group.id),)
                mo = self.env['mrp.production'].sudo().search(domain, limit=1)
            if not mo:
                new_productions_values_by_company[procurement.company_id.id].append(rule._prepare_mo_vals(*procurement, bom))
            else:
                self.env['change.production.qty'].sudo().with_context(skip_activity=True).create({
                    'mo_id': mo.id,
                    'product_qty': mo.product_id.uom_id._compute_quantity((mo.product_uom_qty + procurement.product_qty), mo.product_uom_id)
                }).change_prod_qty()

        note_subtype_id = self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note')
        for company_id, productions_values in new_productions_values_by_company.items():
            # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
            productions = self.env['mrp.production'].with_user(SUPERUSER_ID).sudo().with_company(company_id).create(productions_values)
            productions.filtered(self._should_auto_confirm_procurement_mo).action_confirm()

            for production in productions:
                origin_production = production.move_dest_ids and production.move_dest_ids[0].raw_material_production_id or False
                orderpoint = production.orderpoint_id
                if orderpoint and orderpoint.create_uid.id == SUPERUSER_ID and orderpoint.trigger == 'manual':
                    production.message_post(
                        body=_('This production order has been created from Replenishment Report.'),
                        message_type='comment',
                        subtype_id=note_subtype_id
                    )
                elif orderpoint:
                    production.message_post_with_source(
                        'mail.message_origin_link',
                        render_values={'self': production, 'origin': orderpoint},
                        subtype_id=note_subtype_id,
                    )
                elif origin_production:
                    production.message_post_with_source(
                        'mail.message_origin_link',
                        render_values={'self': production, 'origin': origin_production},
                        subtype_id=note_subtype_id,
                    )
        return True

    @api.model
    def _run_pull(self, procurements):
        # Override to correctly assign the move generated from the pull
        # in its production order (pbm_sam only)
        for procurement, rule in procurements:
            warehouse_id = rule.warehouse_id
            if not warehouse_id:
                warehouse_id = rule.location_dest_id.warehouse_id
            manu_rule = rule.route_id.rule_ids.filtered(lambda r: r.action == 'manufacture' and r.warehouse_id == warehouse_id)
            if warehouse_id.manufacture_steps != 'pbm_sam' or not manu_rule:
                continue
            if rule.picking_type_id == warehouse_id.sam_type_id or (
                warehouse_id.sam_loc_id and warehouse_id.sam_loc_id.parent_path in rule.location_src_id.parent_path
            ):
                if float_compare(procurement.product_qty, 0, precision_rounding=procurement.product_uom.rounding) < 0:
                    procurement.values['group_id'] = procurement.values['group_id'].stock_move_ids.filtered(
                        lambda m: m.state not in ['done', 'cancel']).move_orig_ids.group_id[:1]
                    continue
                manu_type_id = manu_rule[0].picking_type_id
                if manu_type_id:
                    name = manu_type_id.sequence_id.next_by_id()
                else:
                    name = self.env['ir.sequence'].next_by_code('mrp.production') or _('New')
                # Create now the procurement group that will be assigned to the new MO
                # This ensure that the outgoing move PostProduction -> Stock is linked to its MO
                # rather than the original record (MO or SO)
                group = procurement.values.get('group_id')
                if group:
                    procurement.values['group_id'] = group.copy({'name': name})
                else:
                    procurement.values['group_id'] = self.env["procurement.group"].create({'name': name})
        return super()._run_pull(procurements)

    def _get_custom_move_fields(self):
        fields = super(StockRule, self)._get_custom_move_fields()
        fields += ['bom_line_id']
        return fields

    def _get_matching_bom(self, product_id, company_id, values):
        if values.get('bom_id', False):
            return values['bom_id']
        if values.get('orderpoint_id', False) and values['orderpoint_id'].bom_id:
            return values['orderpoint_id'].bom_id
        return self.env['mrp.bom']._bom_find(product_id, picking_type=self.picking_type_id, bom_type='normal', company_id=company_id.id)[product_id]

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom):
        date_planned = self._get_date_planned(bom, values)
        date_deadline = values.get('date_deadline') or date_planned + relativedelta(days=bom.produce_delay)
        mo_values = {
            'origin': origin,
            'product_id': product_id.id,
            'product_description_variants': values.get('product_description_variants'),
            'product_qty': product_uom._compute_quantity(product_qty, bom.product_uom_id) if bom else product_qty,
            'product_uom_id': bom.product_uom_id.id if bom else product_uom.id,
            'location_src_id': self.location_src_id.id or self.picking_type_id.default_location_src_id.id or location_dest_id.id,
            'location_dest_id': location_dest_id.id,
            'bom_id': bom.id,
            'date_deadline': date_deadline,
            'date_start': date_planned,
            'date_finished': fields.Datetime.from_string(values['date_planned']),
            'procurement_group_id': False,
            'propagate_cancel': self.propagate_cancel,
            'orderpoint_id': values.get('orderpoint_id', False) and values.get('orderpoint_id').id,
            'picking_type_id': self.picking_type_id.id or values['warehouse_id'].manu_type_id.id,
            'company_id': company_id.id,
            'move_dest_ids': values.get('move_dest_ids') and [(4, x.id) for x in values['move_dest_ids']] or False,
            'user_id': False,
        }
        # Use the procurement group created in _run_pull mrp override
        # Preserve the origin from the original stock move, if available
        if location_dest_id.warehouse_id.manufacture_steps == 'pbm_sam' and values.get('move_dest_ids') and values.get('group_id') and values['move_dest_ids'][0].origin != values['group_id'].name:
            origin = values['move_dest_ids'][0].origin
            mo_values.update({
                'name': values['group_id'].name,
                'procurement_group_id': values['group_id'].id,
                'origin': origin,
            })
        return mo_values

    def _get_date_planned(self, bom_id, values):
        format_date_planned = fields.Datetime.from_string(values['date_planned'])
        date_planned = format_date_planned - relativedelta(days=bom_id.produce_delay)
        if date_planned == format_date_planned:
            date_planned = date_planned - relativedelta(hours=1)
        return date_planned

    def _get_lead_days(self, product, **values):
        """Add the product and company manufacture delay to the cumulative delay
        and cumulative description.
        """
        delays, delay_description = super()._get_lead_days(product, **values)
        bypass_delay_description = self.env.context.get('bypass_delay_description')
        manufacture_rule = self.filtered(lambda r: r.action == 'manufacture')
        if not manufacture_rule:
            return delays, delay_description
        manufacture_rule.ensure_one()
        bom = values.get('bom') or self.env['mrp.bom']._bom_find(product, picking_type=manufacture_rule.picking_type_id, company_id=manufacture_rule.company_id.id)[product]
        manufacture_delay = bom.produce_delay
        delays['total_delay'] += manufacture_delay
        delays['manufacture_delay'] += manufacture_delay
        if not bypass_delay_description:
            delay_description.append((_('Manufacturing Lead Time'), _('+ %d day(s)', manufacture_delay)))
        if bom.type == 'normal':
            # pre-production rules
            warehouse = self.location_dest_id.warehouse_id
            for wh in warehouse:
                if wh.manufacture_steps != 'mrp_one_step':
                    wh_manufacture_rules = product._get_rules_from_location(product.property_stock_production, route_ids=wh.pbm_route_id)
                    extra_delays, extra_delay_description = (wh_manufacture_rules - self)._get_lead_days(product, **values)
                    for key, value in extra_delays.items():
                        delays[key] += value
                    delay_description += extra_delay_description
            # manufacturing security lead time
            for comp in self.picking_type_id.company_id:
                security_delay = comp.manufacturing_lead
                delays['total_delay'] += security_delay
                delays['security_lead_days'] += security_delay
            if not bypass_delay_description:
                delay_description.append((_('Manufacture Security Lead Time'), _('+ %d day(s)', security_delay)))
        days_to_order = values.get('days_to_order', bom.days_to_prepare_mo)
        delays['total_delay'] += days_to_order
        if not bypass_delay_description:
            delay_description.append((_('Days to Supply Components'), _('+ %d day(s)', days_to_order)))
        return delays, delay_description

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        new_move_vals['production_id'] = False
        return new_move_vals


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    mrp_production_ids = fields.One2many('mrp.production', 'procurement_group_id')

    @api.model
    def run(self, procurements, raise_user_error=True):
        """ If 'run' is called on a kit, this override is made in order to call
        the original 'run' method with the values of the components of that kit.
        """
        procurements_without_kit = []
        product_by_company = defaultdict(OrderedSet)
        for procurement in procurements:
            product_by_company[procurement.company_id].add(procurement.product_id.id)
        kits_by_company = {
            company: self.env['mrp.bom']._bom_find(self.env['product.product'].browse(product_ids), company_id=company.id, bom_type='phantom')
            for company, product_ids in product_by_company.items()
        }
        for procurement in procurements:
            bom_kit = kits_by_company[procurement.company_id].get(procurement.product_id)
            if bom_kit:
                order_qty = procurement.product_uom._compute_quantity(procurement.product_qty, bom_kit.product_uom_id, round=False)
                qty_to_produce = (order_qty / bom_kit.product_qty)
                boms, bom_sub_lines = bom_kit.explode(procurement.product_id, qty_to_produce)
                for bom_line, bom_line_data in bom_sub_lines:
                    bom_line_uom = bom_line.product_uom_id
                    quant_uom = bom_line.product_id.uom_id
                    # recreate dict of values since each child has its own bom_line_id
                    values = dict(procurement.values, bom_line_id=bom_line.id)
                    component_qty, procurement_uom = bom_line_uom._adjust_uom_quantities(bom_line_data['qty'], quant_uom)
                    procurements_without_kit.append(self.env['procurement.group'].Procurement(
                        bom_line.product_id, component_qty, procurement_uom,
                        procurement.location_id, procurement.name,
                        procurement.origin, procurement.company_id, values))
            else:
                procurements_without_kit.append(procurement)
        return super(ProcurementGroup, self).run(procurements_without_kit, raise_user_error=raise_user_error)

    def _get_moves_to_assign_domain(self, company_id):
        domain = super(ProcurementGroup, self)._get_moves_to_assign_domain(company_id)
        domain = expression.AND([domain, [('production_id', '=', False)]])
        return domain
