# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockRule(models.Model):
    _inherit = 'stock.rule'
    action = fields.Selection(selection_add=[('manufacture', 'Manufacture')])

    def _get_message_dict(self):
        message_dict = super(StockRule, self)._get_message_dict()
        source, destination, operation = self._get_message_values()
        manufacture_message = _('When products are needed in <b>%s</b>, <br/> a manufacturing order is created to fulfill the need.') % (destination)
        if self.location_src_id:
            manufacture_message += _(' <br/><br/> The components will be taken from <b>%s</b>.') % (source)
        message_dict.update({
            'manufacture': manufacture_message
        })
        return message_dict

    @api.onchange('action')
    def _onchange_action_operation(self):
        domain = {'picking_type_id': []}
        if self.action == 'manufacture':
            domain = {'picking_type_id': [('code', '=', 'mrp_operation')]}
        return {'domain': domain}

    @api.multi
    def _run_manufacture(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        Production = self.env['mrp.production']
        ProductionSudo = Production.sudo().with_context(force_company=values['company_id'].id)
        bom = self._get_matching_bom(product_id, values)
        if not bom:
            msg = _('There is no Bill of Material found for the product %s. Please define a Bill of Material for this product.') % (product_id.display_name,)
            raise UserError(msg)

        # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
        production = ProductionSudo.create(self._prepare_mo_vals(product_id, product_qty, product_uom, location_id, name, origin, values, bom))
        production.move_raw_ids = self.env['stock.move'].create(production._get_moves_raw_values())
        production.action_confirm()
        origin_production = values.get('move_dest_ids') and values['move_dest_ids'][0].raw_material_production_id or False
        orderpoint = values.get('orderpoint_id')
        if orderpoint:
            production.message_post_with_view('mail.message_origin_link',
                                              values={'self': production, 'origin': orderpoint},
                                              subtype_id=self.env.ref('mail.mt_note').id)
        if origin_production:
            production.message_post_with_view('mail.message_origin_link',
                                              values={'self': production, 'origin': origin_production},
                                              subtype_id=self.env.ref('mail.mt_note').id)
        return True

    @api.multi
    def _get_matching_bom(self, product_id, values):
        if values.get('bom_id', False):
            return values['bom_id']
        return self.env['mrp.bom'].with_context(
            company_id=values['company_id'].id, force_company=values['company_id'].id
        )._bom_find(product=product_id, picking_type=self.picking_type_id, bom_type='normal')  # TDE FIXME: context bullshit

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, values, bom):
        return {
            'origin': origin,
            'product_id': product_id.id,
            'product_qty': product_qty,
            'product_uom_id': product_uom.id,
            'location_src_id': self.location_src_id.id or self.picking_type_id.default_location_src_id.id or location_id.id,
            'location_dest_id': location_id.id,
            'bom_id': bom.id,
            'date_planned_start': fields.Datetime.to_string(self._get_date_planned(product_id, values)),
            'date_planned_finished': values['date_planned'],
            'procurement_group_id': False,
            'propagate': self.propagate,
            'picking_type_id': self.picking_type_id.id or values['warehouse_id'].manu_type_id.id,
            'company_id': values['company_id'].id,
            'move_dest_ids': values.get('move_dest_ids') and [(4, x.id) for x in values['move_dest_ids']] or False,
        }

    def _get_date_planned(self, product_id, values):
        format_date_planned = fields.Datetime.from_string(values['date_planned'])
        date_planned = format_date_planned - relativedelta(days=product_id.produce_delay or 0.0)
        date_planned = date_planned - relativedelta(days=values['company_id'].manufacturing_lead)
        return date_planned

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        new_move_vals['production_id'] = False
        return new_move_vals

class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def run(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        """ If 'run' is called on a kit, this override is made in order to call
        the original 'run' method with the values of the components of that kit.
        """
        bom_kit = self.env['mrp.bom']._bom_find(product=product_id, bom_type='phantom')
        if bom_kit:
            order_qty = product_uom._compute_quantity(product_qty, bom_kit.product_uom_id, round=False)
            qty_to_produce = ( order_qty / bom_kit.product_qty)
            boms, bom_sub_lines = bom_kit.explode(product_id, qty_to_produce)
            for bom_line, bom_line_data in bom_sub_lines:
                bom_line_uom = bom_line.product_uom_id
                quant_uom =  bom_line.product_id.uom_id
                component_qty, procurement_uom = bom_line_uom._adjust_uom_quantities(bom_line_data['qty'], quant_uom)
                super(ProcurementGroup, self).run(bom_line.product_id, component_qty, procurement_uom, location_id, name, origin, values)
            return True
        else:
            return super(ProcurementGroup, self).run(product_id, product_qty, product_uom, location_id, name, origin, values)
