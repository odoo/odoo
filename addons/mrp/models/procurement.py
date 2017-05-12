# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    @api.model
    def _get_action(self):
        return [('manufacture', _('Manufacture'))] + super(ProcurementRule, self)._get_action()


class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    bom_id = fields.Many2one('mrp.bom', 'BoM', index=True, ondelete='cascade')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order')

    @api.multi
    def propagate_cancels(self):
        cancel_man_orders = self.filtered(lambda procurement: procurement.rule_id.action == 'manufacture' and procurement.production_id).mapped('production_id')
        if cancel_man_orders:
            cancel_man_orders.action_cancel()
        return super(ProcurementOrder, self).propagate_cancels()

    @api.multi
    def _run(self):
        self.ensure_one()
        if self.rule_id.action == 'manufacture':
            # make a manufacturing order for the procurement
            return self.make_mo()[self.id]
        return super(ProcurementOrder, self)._run()

    @api.multi
    def _check(self):
        return self.production_id.state == 'done' or super(ProcurementOrder, self)._check()

    @api.multi
    def _get_matching_bom(self):
        """ Finds the bill of material for the product from procurement order. """
        if self.bom_id:
            return self.bom_id
        return self.env['mrp.bom'].with_context(
            company_id=self.company_id.id, force_company=self.company_id.id
        )._bom_find(product=self.product_id, picking_type=self.rule_id.picking_type_id)  # TDE FIXME: context bullshit

    def _get_date_planned(self):
        format_date_planned = fields.Datetime.from_string(self.date_planned)
        date_planned = format_date_planned - relativedelta(days=self.product_id.produce_delay or 0.0)
        date_planned = date_planned - relativedelta(days=self.company_id.manufacturing_lead)
        return date_planned

    def _prepare_mo_vals(self, bom):
        return {
            'origin': self.origin,
            'product_id': self.product_id.id,
            'product_qty': self.product_qty,
            'product_uom_id': self.product_uom.id,
            'location_src_id': self.rule_id.location_src_id.id or self.location_id.id,
            'location_dest_id': self.location_id.id,
            'bom_id': bom.id,
            'date_planned_start': fields.Datetime.to_string(self._get_date_planned()),
            'date_planned_finished': self.date_planned,
            'procurement_group_id': self.group_id.id,
            'propagate': self.rule_id.propagate,
            'picking_type_id': self.rule_id.picking_type_id.id or self.warehouse_id.manu_type_id.id,
            'company_id': self.company_id.id,
            'procurement_ids': [(6, 0, [self.id])],
        }

    @api.multi
    def make_mo(self):
        """ Create production orders from procurements """
        res = {}
        Production = self.env['mrp.production']
        for procurement in self:
            ProductionSudo = Production.sudo().with_context(force_company=procurement.company_id.id)
            bom = procurement._get_matching_bom()
            if bom:
                # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
                production = ProductionSudo.create(procurement._prepare_mo_vals(bom))
                res[procurement.id] = production.id
                procurement.message_post(body=_("Manufacturing Order <em>%s</em> created.") % (production.name))
            else:
                res[procurement.id] = False
                procurement.message_post(body=_("No BoM exists for this product!"))
        return res
