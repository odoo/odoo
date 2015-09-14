# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseRequisitionPartner(models.Model):
    _name = "purchase.requisition.partner"
    _description = "Purchase Requisition Partner"

    partner_ids = fields.Many2many('res.partner', 'purchase_requisition_supplier_rel', 'requisition_id', 'partner_id', string='Vendors', required=True, domain=[('supplier', '=', True)])

    @api.model
    def view_init(self, fields_list):
        res = super(PurchaseRequisitionPartner, self).view_init(fields_list)
        tender = self.env['purchase.requisition'].browse(self.env.context.get('active_id'))
        if not tender.line_ids:
            raise UserError(_('Define product(s) you want to include in the call for tenders.'))
        return res

    @api.multi
    def create_order(self):
        self.ensure_one()
        requisitions = self.env['purchase.requisition'].browse(self.env.context.get('active_ids'))
        for partner in self.partner_ids:
            requisitions.make_purchase_order(partner.id)
        return {'type': 'ir.actions.act_window_close'}
