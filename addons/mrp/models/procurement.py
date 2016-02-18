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
    bom_id = fields.Many2one('mrp.bom', string='BoM', ondelete='cascade', index=True)
    property_ids = fields.Many2many('mrp.property', 'procurement_property_rel', 'procurement_id', 'property_id', string='Properties')
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order')

    @api.multi
    def propagate_cancels(self):
        for procurement in self:
            if procurement.rule_id.action == 'manufacture' and procurement.production_id:
                procurement.production_id.action_cancel()
        return super(ProcurementOrder, self).propagate_cancels()

    @api.multi
    def _run(self):
        self.ensure_one()
        if self.rule_id and self.rule_id.action == 'manufacture':
            #make a manufacturing order for the procurement
            return self.make_mo()[self.id]
        return super(ProcurementOrder, self)._run()

    @api.multi
    def _check(self):
        self.ensure_one()
        if self.production_id and self.production_id.state == 'done':  # TOCHECK: no better method?
            return True
        return super(ProcurementOrder, self)._check()

    def check_bom_exists(self):
        """ Finds the bill of material for the product from procurement order.
        :return: True or False
        """
        for procurement in self:
            bom = self.env['mrp.bom']._bom_find(product=procurement.product_id, properties=procurement.property_ids)
            if not bom:
                return False
        return True

    def _get_date_planned(self):
        format_date_planned = fields.Datetime.from_string(self.date_planned)
        date_planned = format_date_planned - relativedelta(days=self.product_id.produce_delay or 0.0)
        date_planned = date_planned - relativedelta(days=self.company_id.manufacturing_lead)
        return date_planned

    def _prepare_mo_vals(self):
        res_id = self.move_dest_id and self.move_dest_id.id or False
        newdate = self._get_date_planned()
        if self.bom_id:
            bom = self.bom_id
            routing_id = self.bom_id.routing_id.id
        else:
            bom = self.env['mrp.bom'].with_context(dict(force_company=self.company_id.id))._bom_find(product=self.product_id, properties=self.property_ids)
            routing_id = bom.routing_id.id
        return {
            'origin': self.origin,
            'product_id': self.product_id.id,
            'product_qty': self.product_qty,
            'product_uom_id': self.product_uom.id,
            'location_src_id': self.rule_id.location_src_id.id or self.location_id.id,
            'location_dest_id': self.location_id.id,
            'bom_id': bom.id,
            'routing_id': routing_id,
            'date_planned': fields.Datetime.to_string(newdate),
            'move_prod_id': res_id,
            'company_id': self.company_id.id,
        }

    def make_mo(self):
        """ Make Manufacturing(production) order from procurement
        :return: New created Production Orders procurement wise
        """
        res = {}
        for procurement in self:
            if procurement.check_bom_exists():
                # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
                vals = procurement._prepare_mo_vals()
                produce_id = self.env['mrp.production'].sudo().with_context(dict(force_company=procurement.company_id.id)).create(vals)
                res[procurement.id] = produce_id
                procurement.write({'production_id': produce_id.id})
                procurement.message_post(body=_("Manufacturing Order <em>%s</em> created.") % (procurement.production_id.name,))
                produce_id.action_compute(properties=procurement.property_ids)
                produce_id.signal_workflow('button_confirm')
            else:
                res[procurement.id] = False
                procurement.message_post(body=_("No BoM exists for this product!"))
        return res
