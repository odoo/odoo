# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'
    action = fields.Selection(selection_add=[('manufacture', 'Manufacture')])

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
        )._bom_find(product=product_id, picking_type=self.picking_type_id)  # TDE FIXME: context bullshit

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, values, bom):
        return {
            'origin': origin,
            'product_id': product_id.id,
            'product_qty': product_qty,
            'product_uom_id': product_uom.id,
            'location_src_id': self.location_src_id.id or location_id.id,
            'location_dest_id': location_id.id,
            'bom_id': bom.id,
            'date_planned_start': fields.Datetime.to_string(self._get_date_planned(product_id, values)),
            'date_planned_finished': values['date_planned'],
            'procurement_group_id': values.get('group_id').id if values.get('group_id', False) else False,
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
