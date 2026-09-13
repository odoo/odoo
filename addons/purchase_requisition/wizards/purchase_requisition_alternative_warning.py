from odoo import fields, models


class PurchaseRequisitionAlternativeWarning(models.TransientModel):
    _name = "purchase.requisition.alternative.warning"
    _description = "Wizard in case PO still has open alternative requests for quotation"

    po_ids = fields.Many2many(
        comodel_name="purchase.order",
        relation="warning_purchase_order_rel",
        string="POs to Confirm",
    )
    alternative_po_ids = fields.Many2many(
        comodel_name="purchase.order",
        relation="warning_purchase_order_alternative_rel",
        string="Alternative POs",
    )

    def action_keep_alternatives(self):
        return self._action_done()

    def action_cancel_alternatives(self):
        self.alternative_po_ids.filtered(
            lambda po: po.state == "draft" and po.id not in self.po_ids.ids
        ).action_cancel()
        return self._action_done()

    def _action_done(self):
        return self.po_ids.with_context(
            {"skip_alternative_check": True}
        ).action_confirm()
