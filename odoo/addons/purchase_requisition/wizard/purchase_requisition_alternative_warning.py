# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseRequisitionAlternativeWarning(models.TransientModel):
    _name = 'purchase.requisition.alternative.warning'
    _description = 'Wizard in case PO still has open alternative requests for quotation'

    po_ids = fields.Many2many('purchase.order', 'warning_purchase_order_rel', string="POs to Confirm")
    alternative_po_ids = fields.Many2many('purchase.order', 'warning_purchase_order_alternative_rel', string="Alternative POs")

    def action_keep_alternatives(self):
        return self._action_done()

    def action_cancel_alternatives(self):
        # in theory alternative_po_ids shouldn't have any po_ids in it, but it's possible by accident/forcing it, so avoid cancelling them to be safe
        self.alternative_po_ids.filtered(lambda po: po.state in ['draft', 'sent', 'to approve'] and po.id not in self.po_ids.ids).button_cancel()
        return self._action_done()

    def _action_done(self):
        return self.po_ids.with_context({'skip_alternative_check': True}).button_confirm()
