from odoo import _, api, fields, models

class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'l10n_es_edi_verifactu.record_mixin']

    l10n_es_edi_verifactu_state = fields.Selection(tracking=True)  # defined in 'l10n_es_edi_verifactu.record_mixin'

    l10n_es_edi_verifactu_show_cancel_button = fields.Boolean(
        string="Show Veri*Factu Cancel Button",
        compute='_compute_l10n_es_edi_verifactu_show_cancel_button',
    )

    @api.depends('country_code')
    def _compute_l10n_es_edi_verifactu_required(self):
        # Overrides verifactu_record_mixin.py
        for move in self:
            move.l10n_es_edi_verifactu_required = move.country_code == 'ES'

    @api.depends('company_id', 'name', 'invoice_date', 'amount_total_signed')
    def _compute_l10n_es_edi_verifactu_record_identifier(self):
        # Overrides verifactu_record_mixin.py
        for move in self:
            if not move.l10n_es_edi_verifactu_required:
                identifier = False
            elif move.state == 'draft':
                identifier = {
                    'errors': [_("The invoice is in draft.")]
                }
            else:
                identifier = self.env['l10n_es_edi_verifactu.document']._record_identifier(
                    move.company_id, move.name, move.invoice_date, move.amount_total_signed
                )
            move.l10n_es_edi_verifactu_record_identifier = identifier

    @api.depends('l10n_es_edi_verifactu_state')
    def _compute_show_reset_to_draft_button(self):
        """ Disallow resetting to draft in case the corresponding billing record is already
            registerd with the AEAT or there is an ongoing registration request."""
        # EXTENDS 'account'
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted'):
                move.show_reset_to_draft_button = False

    @api.depends('l10n_es_edi_verifactu_state')
    def _compute_l10n_es_edi_verifactu_show_cancel_button(self):
        for move in self:
            move.l10n_es_edi_verifactu_show_cancel_button = move.l10n_es_edi_verifactu_state in ('registered_with_errors', 'accepted')

    def _l10n_es_edi_verifactu_get_record_values(self, cancellation=False):
        self.ensure_one()
        invoice = self
        invoice = invoice.with_context(lang=invoice.partner_id.lang)

        errors = []

        company = invoice.company_id
        if not company:
            errors.append(_("Please set a company on the invoice."))
            return {}, errors

        record_identifier = invoice.l10n_es_edi_verifactu_record_identifier
        errors.extend(record_identifier['errors'])

        is_simplified = invoice.l10n_es_is_simplified

        vals = {
            'cancellation': cancellation,
            'company': company,
            'delivery_date': invoice.delivery_date,
            'description': invoice.invoice_origin[:500] if invoice.invoice_origin else None,
            'identifier': record_identifier,
            'invoice_date': invoice.invoice_date,
            'is_simplified': is_simplified,
            'move_type': invoice.move_type,
            'name': invoice.name,
            'partner': invoice.commercial_partner_id,
            'record': invoice,
            'rejected_before': False,  # TODO:
            'refunded_record': invoice.reversed_entry_id,
            'verifactu_state': invoice.l10n_es_edi_verifactu_state,
        }

        tax_details_functions = self.env['account.tax']._l10n_es_edi_verifactu_get_tax_details_functions()

        vals['tax_details'] = invoice._prepare_invoice_aggregated_taxes(
            filter_invl_to_apply=tax_details_functions['full_filter_invl_to_apply'],
            filter_tax_values_to_apply=tax_details_functions['filter_to_apply'],
            grouping_key_generator=tax_details_functions['grouping_key_generator'],
        )

        return vals, errors

    def l10n_es_edi_verifactu_button_cancel(self):
        self.l10n_es_edi_verifactu_mark_for_next_batch(cancellation=True)
