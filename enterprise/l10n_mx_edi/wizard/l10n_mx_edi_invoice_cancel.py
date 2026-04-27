from odoo import _, api, fields, models
from odoo.addons.l10n_mx_edi.models.l10n_mx_edi_document import (
    CANCELLATION_REASON_SELECTION,
    CANCELLATION_REASON_DESCRIPTION,
    GLOBAL_INVOICE_PERIODICITY_DEFAULT_VALUES,
)
from odoo.exceptions import UserError


class L10nMxEdiInvoiceCancel(models.TransientModel):
    _name = 'l10n_mx_edi.invoice.cancel'
    _description = "Request CFDI Cancellation"

    document_id = fields.Many2one(comodel_name='l10n_mx_edi.document')
    mode = fields.Selection(
        selection=[
            ('invoice', 'invoice'),
            ('invoice_with_replacement', 'invoice_with_replacement'),
            ('ginvoice', 'ginvoice'),
            ('ginvoice_with_replacement', 'ginvoice_with_replacement'),
        ],
        compute='_compute_mode',
        required=True,
        store=True,
        precompute=True,
    )
    available_cancellation_reasons = fields.Char(compute='_compute_available_cancellation_reasons')
    cancellation_reason = fields.Selection(
        selection=CANCELLATION_REASON_SELECTION,
        string="Reason",
        compute='_compute_cancellation_reason',
        store=True,
        readonly=False,
        precompute=True,
        required=True,
        help=CANCELLATION_REASON_DESCRIPTION,
    )
    periodicity = fields.Selection(**GLOBAL_INVOICE_PERIODICITY_DEFAULT_VALUES)
    need_replacement_invoice_button = fields.Boolean(compute='_compute_need_replacement_invoice_button')

    @api.depends('document_id')
    def _compute_mode(self):
        for wizard in self:
            doc = wizard.document_id
            if doc.state == 'invoice_sent':
                substitution_doc = doc._get_substitution_document()
                wizard.mode = 'invoice_with_replacement' if substitution_doc else 'invoice'
            elif doc.state == 'ginvoice_sent':
                substitution_doc = doc._get_substitution_document()
                wizard.mode = 'ginvoice_with_replacement' if substitution_doc else 'ginvoice'
            else:
                raise UserError(_("The input document is invalid"))

    @api.depends('mode')
    def _compute_available_cancellation_reasons(self):
        for wizard in self:
            if wizard.mode in ('invoice_with_replacement', 'ginvoice_with_replacement'):
                wizard.available_cancellation_reasons = '01'
            elif wizard.mode == 'invoice':
                wizard.available_cancellation_reasons = '01,02,03,04'
            elif wizard.document_id.state == 'ginvoice_sent':
                wizard.available_cancellation_reasons = '01,02,04'

    @api.depends('available_cancellation_reasons')
    def _compute_cancellation_reason(self):
        for wizard in self:
            wizard.cancellation_reason = wizard.available_cancellation_reasons.split(',')[0]

    @api.depends('mode', 'cancellation_reason')
    def _compute_need_replacement_invoice_button(self):
        for wizard in self:
            wizard.need_replacement_invoice_button = (
                wizard.cancellation_reason == '01'
                and wizard.mode in ('invoice', 'ginvoice')
            )

    def action_create_replacement_invoice(self):
        self.ensure_one()
        if self.mode == 'invoice':
            invoice = self.document_id.move_id
            new_invoice_data = invoice\
                .with_context(include_business_fields=True)\
                .copy_data({'l10n_mx_edi_cfdi_origin': f'04|{invoice.l10n_mx_edi_cfdi_uuid}'})[0]
            # Only invoice lines have to be copied
            # as we want them to be recomputed using the current currency rate
            new_invoice_data['line_ids'] = [line for line in new_invoice_data['line_ids'] if line[2]['display_type'] in ('product', 'line_section', 'line_note')]
            new_invoice = self.env['account.move'].create(new_invoice_data)

            return {
                'name': _("Replacement Invoice"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': new_invoice.id,
                'view_mode': 'form',
                'context': {'default_move_type': new_invoice.move_type},
            }
        elif self.mode == 'ginvoice':
            records = self.document_id._get_source_records()
            records._l10n_mx_edi_cfdi_global_invoice_try_send(
                periodicity=self.periodicity,
                origin=f'04|{self.document_id.attachment_uuid}',
            )

    def action_cancel_invoice(self):
        self.ensure_one()
        if self.cancellation_reason == '01' and self.mode not in ('invoice_with_replacement', 'ginvoice_with_replacement'):
            return
        records = self.document_id._get_source_records()
        if self.mode.startswith('invoice'):
            records._l10n_mx_edi_cfdi_invoice_try_cancel(self.document_id, self.cancellation_reason)
        elif self.document_id.state == 'ginvoice_sent':
            records._l10n_mx_edi_cfdi_global_invoice_try_cancel(self.document_id, self.cancellation_reason)
