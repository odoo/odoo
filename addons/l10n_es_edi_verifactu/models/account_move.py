from odoo import _, api, fields, models

class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'l10n_es_edi_verifactu.record_mixin']

    l10n_es_edi_verifactu_state = fields.Selection(tracking=True)  # defined in 'l10n_es_edi_verifactu.record_mixin'

    @api.depends('country_code')
    def _compute_l10n_es_edi_verifactu_required(self):
        # Overrides verifactu_record_mixin.py
        for move in self:
            move.l10n_es_edi_verifactu_required = move.country_code == 'ES' and move.company_id.l10n_es_edi_verifactu_required

    @api.depends('l10n_es_edi_verifactu_state', 'l10n_es_edi_verifactu_record_document_ids', 'l10n_es_edi_verifactu_record_document_ids.state')
    def _compute_show_reset_to_draft_button(self):
        """
        Disallow resetting to draft in the following cases:
        * The move is registered with the AEAT
        * We are waiting to sent a record document (registration) to the AEAT.
        """
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted'):
                move.show_reset_to_draft_button = False
            waiting_record_documents = move.l10n_es_edi_verifactu_record_document_ids.filtered(lambda rd: not rd.state)
            if waiting_record_documents:
                move.show_reset_to_draft_button = False

    def _l10n_es_edi_verifactu_get_record_values(self, cancellation=False):
        vals, errors = super()._l10n_es_edi_verifactu_get_record_values(cancellation=cancellation)

        invoice = self
        invoice = invoice.with_context(lang=invoice.partner_id.lang)

        if invoice.state != 'posted':
            errors.append(_("Veri*Factu records can only be generated for posted invoices."))
            return {}, errors

        company = invoice.company_id
        if not company:
            errors.append(_("Please set a company on the invoice."))
            return {}, errors

        is_simplified = invoice.l10n_es_is_simplified

        vals.update({
            'company': company,
            'delivery_date': invoice.delivery_date,
            'description': invoice.invoice_origin[:500] if invoice.invoice_origin else None,
            'invoice_date': invoice.invoice_date,
            'is_simplified': is_simplified,
            'move_type': invoice.move_type,
            'name': invoice.name,
            'partner': invoice.commercial_partner_id,
            'refunded_record': invoice.reversed_entry_id,
        })

        tax_details_functions = self.env['account.tax']._l10n_es_edi_verifactu_get_tax_details_functions()

        vals['tax_details'] = invoice._prepare_invoice_aggregated_taxes(
            filter_invl_to_apply=tax_details_functions['full_filter_invl_to_apply'],
            filter_tax_values_to_apply=tax_details_functions['filter_to_apply'],
            grouping_key_generator=tax_details_functions['grouping_key_generator'],
        )

        return vals, errors
