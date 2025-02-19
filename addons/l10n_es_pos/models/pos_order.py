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

    def _generate_pos_order_invoice(self):
        # Extend 'point_of_sale'
        # Add the simplified partner in case we do a simplified invoice and no partner is set
        if not self.config_id.is_spanish:
            return super()._generate_pos_order_invoice()
        for order in self:
            if order.account_move or not order.to_invoice or not order.is_l10n_es_simplified_invoice:
                continue
            if not order.partner_id:
                order.partner_id = self.config_id.simplified_partner_id
        return super()._generate_pos_order_invoice()

    def _prepare_invoice_vals(self):
        res = super()._prepare_invoice_vals()
        if self.config_id.is_spanish and self.is_l10n_es_simplified_invoice:
            res["journal_id"] = self.config_id.l10n_es_simplified_invoice_journal_id.id
        return res

    def get_invoice_name(self):
        return self.account_move.name
