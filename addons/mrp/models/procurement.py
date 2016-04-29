# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    @api.model
    def _get_action(self):
        return [('manufacture', _('Manufacture'))] + super(ProcurementRule, self)._get_action()


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    bom_id = fields.Many2one('mrp.bom', 'BoM', ondelete='cascade', select=True)
    property_ids = fields.Many2many('mrp.property', 'procurement_property_rel', 'procurement_id','property_id', 'Properties')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order')

    @api.multi
    def propagate_cancels(self):
        to_propagate = self.filtered(lambda procurement: procurement.rule_id.action == 'manufacture' and procurement.production_id).mapped('production_id')
        if to_propagate:
            to_propagate.action_cancel()
        return super(ProcurementOrder, self).propagate_cancels()

    @api.multi
    def _run(self):
        if self.rule_id and self.rule_id.action == 'manufacture':
            # make a manufacturing order for the procurement
            return self.make_mo()[self.id]
        return super(ProcurementOrder, self)._run()

    @api.multi
    def _check(self):
        if self.production_id and self.production_id.state == 'done':  # TOCHECK: no better method? 
            return True
        return super(ProcurementOrder, self)._check()

    @api.multi
    def check_bom_exists(self):
        """ Finds the bill of material for the product from procurement order.
        @return: True or False
        """
        for procurement in self:
            # TDE FIXME: properties -> property_ids
            bom = self.env['mrp.bom']._bom_find(product_id=procurement.product_id.id, properties=procurement.property_ids.ids)
            if not bom:
                return False
        return True

    def _get_date_planned(self):
        format_date_planned = datetime.strptime(self.date_planned,
                                                DEFAULT_SERVER_DATETIME_FORMAT)
        date_planned = format_date_planned - relativedelta(days=self.product_id.produce_delay or 0.0)
        date_planned = date_planned - relativedelta(days=self.company_id.manufacturing_lead)
        return date_planned

    def _prepare_mo_vals(self):
        BoM = self.env['mrp.bom'].with_context(company_id=self.company_id.id)
        if self.bom_id:
            bom = self.bom_id
            routing_id = self.bom_id.routing_id.id
        else:
            bom = BoM._bom_find(product_id=self.product_id.id,
                                properties=self.property_ids.ids)
            routing_id = bom.routing_id.id
        return {
            'origin': self.origin,
            'product_id': self.product_id.id,
            'product_qty': self.product_qty,
            'product_uom': self.product_uom.id,
            'location_src_id': self.rule_id.location_src_id.id or self.location_id.id,
            'location_dest_id': self.location_id.id,
            'bom_id': bom.id,
            'routing_id': routing_id,
            'date_planned': self._get_date_planned().strftime('%Y-%m-%d %H:%M:%S'),  # TDE FIXME: use tools
            'move_prod_id': self.move_dest_id.id,
            'company_id': self.company_id.id,
        }

    @api.multi
    def make_mo(self):
        """ Make Manufacturing(production) order from procurement
        @return: New created Production Orders procurement wise
        """
        res = {}
        Production = self.env['mrp.production']
        for procurement in self:
            ProductionSudo = Production.sudo().with_context(force_company=procurement.company_id.id)
            if procurement.check_bom_exists():
                # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
                production = ProductionSudo.create(procurement._prepare_mo_vals())
                res[procurement.id] = production.id
                procurement.write({'production_id': production.id})
                procurement.message_post(body=_("Manufacturing Order <em>%s</em> created.") % (production.name))
                production.action_compute(properties=procurement.property_ids.ids)
                production.signal_workflow('button_confirm')
            else:
                res[procurement.id] = False
                procurement.message_post(body=_("No BoM exists for this product!"))
        return res
