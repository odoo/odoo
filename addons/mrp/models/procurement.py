# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'
    action = fields.Selection(selection_add=[('manufacture', 'Manufacture')])

class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.multi
    def _run(self, values, rule, doraise=True):
        if rule.action == 'manufacture':
            Production = self.env['mrp.production']
            ProductionSudo = Production.sudo().with_context(force_company=values['company_id'].id)
            bom = self._get_matching_bom(values, rule)
            if not bom:
                msg = _('No Bill of Material found for product %s.') % (values['product_id'].display_name,)
                if doraise:
                    raise UserError(msg)
                else:
                    self.log_next_activity(values['product_id'], msg)
                    return False

            # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
            production = ProductionSudo.create(self._prepare_mo_vals(values, rule, bom))
            origin_production = values.get('move_dest_ids') and values ['move_dest_ids'][0].raw_material_production_id or False
            orderpoint = values.get('orderpoint_id')
            if orderpoint:
                production.message_post_with_view('mail.message_origin_link',
                    values={'self': production, 'origin': orderpoint.id},
                    subtype_id=self.env.ref('mail.mt_note').id)
            if origin_production:
                production.message_post_with_view('mail.message_origin_link',
                    values={'self': production, 'origin': origin_production},
                    subtype_id=self.env.ref('mail.mt_note').id)
            return True
        return super(ProcurementGroup, self)._run(values, rule, doraise)

    @api.multi
    def _get_matching_bom(self, values, rule):
        if values.get('bom_id', False):
            return values['bom_id']
        return self.env['mrp.bom'].with_context(
            company_id=values['company_id'].id, force_company=values['company_id'].id
        )._bom_find(product=values['product_id'], picking_type=rule.picking_type_id)  # TDE FIXME: context bullshit

    def _get_date_planned(self, values, rule):
        format_date_planned = fields.Datetime.from_string(values['date_planned'])
        date_planned = format_date_planned - relativedelta(days=values['product_id'].produce_delay or 0.0)
        date_planned = date_planned - relativedelta(days=values['company_id'].manufacturing_lead)
        return date_planned

    def _prepare_mo_vals(self, values, rule, bom):
        return {
            'origin': values['origin'],
            'product_id': values['product_id'].id,
            'product_qty': values['product_qty'],
            'product_uom_id': values['product_uom'].id,
            'location_src_id': rule.location_src_id.id or values['location_id'].id,
            'location_dest_id': values['location_id'].id,
            'bom_id': bom.id,
            'date_planned_start': fields.Datetime.to_string(self._get_date_planned(values, rule)),
            'date_planned_finished': values['date_planned'],
            'procurement_group_id': values.get('group_id').id if values.get('group_id', False) else False,
            'propagate': rule.propagate,
            'picking_type_id': rule.picking_type_id.id or values['warehouse_id'].manu_type_id.id,
            'company_id': values['company_id'].id,
            'move_dest_ids': values.get('move_dest_ids') and [(4, x.id) for x in values['move_dest_ids']] or False,
        }

