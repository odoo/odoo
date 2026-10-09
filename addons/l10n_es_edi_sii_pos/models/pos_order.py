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

    def _process_saved_order(self, draft):
        if self.l10n_es_sii_required and self.refunded_order_id:
            self.to_invoice = True
            if not self.partner_id:
                simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
                if simplified_partner:
                    self.partner_id = simplified_partner

        return super()._process_saved_order(draft)

    def _prepare_invoice_vals(self):
        res = super()._prepare_invoice_vals()
        if not any(self.mapped('l10n_es_sii_required')):
            return res

        if self.l10n_es_invoice_type:
            res['l10n_es_invoice_type'] = self.l10n_es_invoice_type
        elif not self.refunded_order_id:
            res['l10n_es_invoice_type'] = 'F1'

        return res
