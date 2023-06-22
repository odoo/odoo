from odoo import api, fields, models
from odoo.tools import float_compare


class PosOrder(models.Model):
    _inherit = "pos.order"

    pos_is_spanish = fields.Boolean(
        string="Spanish localization",
        related="config_id.is_spanish",
    )

    is_l10n_es_simplified_invoice = fields.Boolean(
        "Simplified invoice",
        copy=False,
        default=False,
    )
    l10n_es_unique_id = fields.Char(
        "Simplified invoice number",
        copy=False,
    )

    @api.model
    def _simplified_limit_check(self, amount_total, limit):
        return float_compare(amount_total, limit, precision_digits=self.env["decimal.precision"].precision_get("Account")) < 0

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get("l10n_es_unique_id"):
            res.update(
                {
                    "l10n_es_unique_id": ui_order["l10n_es_unique_id"],
                    "is_l10n_es_simplified_invoice": True,
                }
            )
        return res

    @api.model
    def _update_sequence_number(self, pos):
        pos.l10n_es_simplified_invoice_sequence_id.next_by_id()

    @api.model
    def _process_order(self, pos_order, draft, existing_order):
        order_data = pos_order.get("data", {})
        if not order_data.get("l10n_es_unique_id"):
            return super()._process_order(pos_order, draft, existing_order)
        pos = self.env["pos.session"].browse(order_data.get("pos_session_id")).config_id
        if self._simplified_limit_check(order_data.get("amount_total", 0), pos.l10n_es_simplified_invoice_limit):
            pos_order["data"].update({"is_l10n_es_simplified_invoice": True})
            self._update_sequence_number(pos)
        return super()._process_order(pos_order, draft, existing_order)

    def _get_fields_for_draft_order(self):
        fields = super()._get_fields_for_draft_order()
        fields += ["l10n_es_unique_id"]
        return fields

    def _export_for_ui(self, order):
        res = super()._export_for_ui(order)
        if self.config_id.is_spanish:
            res.update({"l10n_es_unique_id": order.l10n_es_unique_id})
        return res
