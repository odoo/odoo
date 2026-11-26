from odoo import fields, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_es_sii_required = fields.Boolean(
        string="SII Required",
        compute='_compute_l10n_es_sii_required',
    )

    def _compute_l10n_es_sii_required(self):
        for order in self:
            order.l10n_es_sii_required = order.company_id._l10n_es_pos_get_fiscal_mode() == 'sii'

    def _l10n_es_sii_prepare_refund(self):
        """SII only accepts refunds as invoices: refunds are always invoiced, by default
        to the generic partner of the simplified invoices.

        Called before the order is paid, so that `l10n_es_edi_pos` sees it as invoiced
        and does not number it in the series of simplified invoices.
        """
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

        invoice_types = set(self.mapped('l10n_es_invoice_type')) - {False}
        if len(invoice_types) == 1:
            res['l10n_es_invoice_type'] = invoice_types.pop()
        elif len(invoice_types) > 1:
            # A corrective invoice carries a single refund reason.
            raise UserError(self.env._("You cannot consolidate orders with different SII refund reasons."))
        elif self.refunded_order_id:
            simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
            if not self.partner_id or self.partner_id == simplified_partner:
                res['l10n_es_invoice_type'] = 'R5'
        else:
            res['l10n_es_invoice_type'] = 'F1'

        return res
