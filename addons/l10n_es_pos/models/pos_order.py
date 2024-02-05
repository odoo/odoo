from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = "pos.order"

    is_l10n_es_simplified_invoice = fields.Boolean("Simplified invoice")
    l10n_es_simplified_invoice_number = fields.Char("Simplified invoice number", compute="_compute_l10n_es_simplified_invoice_number")

    @api.depends("account_move")
    def _compute_l10n_es_simplified_invoice_number(self):
        for order in self:
            if order.is_l10n_es_simplified_invoice:
                order.l10n_es_simplified_invoice_number = order.account_move.name
            else:
                order.l10n_es_simplified_invoice_number = False

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get("is_l10n_es_simplified_invoice"):
            res.update({"is_l10n_es_simplified_invoice": ui_order["is_l10n_es_simplified_invoice"]})
        return res

    def _prepare_invoice_vals(self):
        res = super()._prepare_invoice_vals()
        if self.config_id.is_spanish and self.is_l10n_es_simplified_invoice:
            res["journal_id"] = self.config_id.l10n_es_simplified_invoice_journal_id.id
        return res

    def get_invoice_name(self):
        return self.account_move.name

    @api.model
    def _get_create_from_ui_returned_fields_name(self):
        fields_name = super()._get_create_from_ui_returned_fields_name()
        fields_name.append('l10n_es_simplified_invoice_number')
        return fields_name

    def _export_for_ui(self, order):
        res = super()._export_for_ui(order)
        res['l10n_es_simplified_invoice_number'] = order.l10n_es_simplified_invoice_number
        return res
