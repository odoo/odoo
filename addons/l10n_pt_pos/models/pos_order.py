from markupsafe import Markup

from odoo import _, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    l10n_pt_is_reprint = fields.Boolean(readonly=True)

    def _generate_pos_order_invoice(self):
        if self.country_code != 'PT':
            return super()._generate_pos_order_invoice()

        result = super(PosOrder, self.filtered('partner_id').with_context(generate_pdf=False))._generate_pos_order_invoice()

        for order in self.filtered(lambda o: not o.partner_id and not o.account_move):
            move = order._create_invoice({
                'move_type': 'out_receipt',
                'journal_id': order.session_id.config_id.invoice_journal_id.id,
                'invoice_origin': order.name,
                'ref': order.name,
                'currency_id': order.currency_id.id,
                'invoice_date': order.date_order.date(),
                'pos_order_ids': order.ids,
                'invoice_line_ids': order._prepare_invoice_lines(),
            })
            order.state = 'invoiced'
            move.sudo().with_company(order.company_id)._post()

        self.env['account.move']._l10n_pt_compute_missing_hashes()
        return result

    def _l10n_pt_pos_get_vat_exemptions_reasons(self):
        self.ensure_one()
        taxes_with_exemption = self.line_ids.tax_ids.filtered(lambda tax: tax.l10n_pt_tax_exemption_reason)
        return sorted(set(taxes_with_exemption.mapped(
            lambda tax: dict(tax._fields['l10n_pt_tax_exemption_reason'].selection).get(tax.l10n_pt_tax_exemption_reason)
        )))

    def update_l10n_pt_print_version(self):
        self.ensure_one()
        self.l10n_pt_is_reprint = True

    def post_reprint_reason(self, reason):
        self.ensure_one()
        msg = Markup(_("Reason for reprinting document %(name)s:<br/>%(reason)s")) % {
            'name': self.name,
            'reason': reason,
        }
        self.message_post(body=msg)
        return True

    def l10n_pt_get_order_vals(self):
        self.ensure_one()
        invoice = self.account_move
        if not invoice:
            return {}
        doc_type_selection = dict(invoice._fields['l10n_pt_document_type']._description_selection(self.env))
        return {
            'name': self.name,
            'hash_short': invoice.l10n_pt_inalterable_hash_short,
            'atcud': invoice.l10n_pt_atcud,
            'document_identifier': invoice.l10n_pt_document_number,
            'qr_code_str': invoice.l10n_pt_qr_code_str,
            'is_reprint': self.l10n_pt_is_reprint,
            'document_type': doc_type_selection.get(invoice.l10n_pt_document_type, ''),
            'training_mode': invoice.l10n_pt_at_series_id.training_series if invoice.l10n_pt_at_series_id else False,
        }
