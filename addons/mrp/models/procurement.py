# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from openerp import api, fields, models, _


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    @api.model
    def _get_action(self):
        return [('manufacture', _('Manufacture'))] + super(ProcurementRule, self)._get_action()


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'
    bom_id = fields.Many2one('mrp.bom', string='BoM', ondelete='cascade', select=True)
    property_ids = fields.Many2many('mrp.property', 'procurement_property_rel', 'procurement_id', 'property_id', string='Properties')
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order')

    @api.one
    def propagate_cancels(self):
        for procurement in self:
            if procurement.rule_id.action == 'manufacture' and procurement.production_id:
                self.env['mrp.production'].browse(procurement.production_id.id).action_cancel()
        return super(ProcurementOrder, self).propagate_cancels()

    @api.model
    def _run(self, procurement):
        if procurement.rule_id and procurement.rule_id.action == 'manufacture':
            #make a manufacturing order for the procurement
            return procurement.make_mo()[procurement.id]
        return super(ProcurementOrder, self)._run(procurement)

    @api.model
    def _check(self, procurement):
        if procurement.production_id and procurement.production_id.state == 'done':  # TOCHECK: no better method? 
            return True
        return super(ProcurementOrder, self)._check(procurement)

    def check_bom_exists(self):
        """ Finds the bill of material for the product from procurement order.
        @return: True or False
        """
        for procurement in self:
            properties = [x.id for x in procurement.property_ids]
            bom_id = self.env['mrp.bom']._bom_find(product_id=procurement.product_id.id, properties=properties)
            if not bom_id:
                return False
        return True

    @api.model
    def _get_date_planned(self, procurement):
        format_date_planned = fields.Datetime.from_string(procurement.date_planned)
        date_planned = format_date_planned - relativedelta(days=procurement.product_id.produce_delay or 0.0)
        date_planned = date_planned - relativedelta(days=procurement.company_id.manufacturing_lead)
        return date_planned

    @api.model
    def _prepare_mo_vals(self, procurement):
        res_id = procurement.move_dest_id and procurement.move_dest_id.id or False
        newdate = self._get_date_planned(procurement)
        MrpBom = self.env['mrp.bom']
        if procurement.bom_id:
            bom_id = procurement.bom_id.id
            routing_id = procurement.bom_id.routing_id.id
        else:
            properties = [x.id for x in procurement.property_ids]
            bom_id = MrpBom.with_context(dict(force_company=procurement.company_id.id))._bom_find(product_id=procurement.product_id.id, properties=properties)
            bom = MrpBom.browse(bom_id)
            routing_id = bom.routing_id.id
        return {
            'origin': procurement.origin,
            'product_id': procurement.product_id.id,
            'product_qty': procurement.product_qty,
            'product_uom_id': procurement.product_uom.id,
            'product_uos_qty': procurement.product_uos and procurement.product_uos_qty or False,
            'product_uos_id': procurement.product_uos and procurement.product_uos.id or False,
            'location_src_id': procurement.location_id.id,
            'location_dest_id': procurement.location_id.id,
            'bom_id': bom_id,
            'routing_id': routing_id,
            'date_planned': fields.Datetime.to_string(newdate),
            'move_prod_id': res_id,
            'company_id': procurement.company_id.id,
        }

    def make_mo(self):
        """ Make Manufacturing(production) order from procurement
        @return: New created Production Orders procurement wise
        """
        res = {}
        for procurement in self:
            if self.check_bom_exists():
                #create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
                vals = self._prepare_mo_vals(procurement)
                produce_id = self.env['mrp.production'].sudo().with_context(dict(force_company=procurement.company_id.id)).create(vals)
                res[procurement.id] = produce_id
                procurement.write({'production_id': produce_id.id})
                self.production_order_create_note(procurement)
                produce_id.action_compute(properties=[x.id for x in procurement.property_ids])
                produce_id.signal_workflow('button_confirm')
            else:
                res[procurement.id] = False
                self.message_post(body=_("No BoM exists for this product!"))
        return res

    @api.model
    def production_order_create_note(self, procurement):
        self.message_post(body=_("Manufacturing Order <em>%s</em> created.") % (procurement.production_id.name,))
