from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_es_sii_required = fields.Boolean(
        string="SII Required",
        related="company_id.l10n_es_sii_required"
    )

    l10n_es_invoice_type = fields.Selection(
        selection="_l10n_es_refund_reason_selection",
        string="SII Refund Reason",
        copy=False
    )

    @api.model
    def _l10n_es_refund_reason_selection(self):
        return self.env['account.move']._l10n_es_refund_reason_selection()

    def _l10n_es_sii_get_ticket_name(self):
        self.ensure_one()
        return f"{self.config_id.id}/{str(self.sequence_number).zfill(6)}"

    def _l10n_es_sii_prepare_refund(self):
        simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
        for order in self:
            if order.l10n_es_sii_required and order.refunded_order_id:
                order.to_invoice = True
                if not order.partner_id and simplified_partner:
                    order.partner_id = simplified_partner
   
    def refund(self):
        action = super().refund()
        if action.get('res_id'):
            self.browse(action['res_id'])._l10n_es_sii_prepare_refund()
        return action

    def _process_saved_order(self, draft):
        self.ensure_one()
        self._l10n_es_sii_prepare_refund()
        return super()._process_saved_order(draft)

    def _prepare_invoice_vals(self):
        res = super()._prepare_invoice_vals()
        if not any(self.mapped('l10n_es_sii_required')):
            return res

        if self.l10n_es_invoice_type:
            res['l10n_es_invoice_type'] = self.l10n_es_invoice_type
        elif self.refunded_order_id:
            simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
            if not self.partner_id or self.partner_id == simplified_partner:
                res['l10n_es_invoice_type'] = 'R5'

        else:
            res['l10n_es_invoice_type'] = 'F1'

        return res

    def _update_sequence_number(self, session, values):
        """ Override: do not allow updating the sequence number for Spanish pos orders"""
        if not session.config_id.l10n_es_sii_required or not values.get('to_invoice'):
            super()._update_sequence_number(session, values)
