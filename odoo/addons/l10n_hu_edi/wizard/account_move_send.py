import time
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import L10nHuEdiConnection


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_hu_edi_actionable_errors = fields.Json(
        compute='_compute_l10n_hu_edi_actionable_errors'
    )
    l10n_hu_edi_enable_nav_30 = fields.Boolean(
        compute='_compute_l10n_hu_edi_enable_nav_30'
    )
    l10n_hu_edi_checkbox_nav_30 = fields.Boolean(
        string='NAV 3.0',
        compute='_compute_l10n_hu_edi_checkbox_nav_30',
        store=True,
        readonly=False,
    )

    def _get_wizard_values(self):
        # EXTENDS 'account'
        return {
            **super()._get_wizard_values(),
            'l10n_hu_edi_checkbox_nav_30': self.l10n_hu_edi_checkbox_nav_30,
        }

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_ids')
    def _compute_l10n_hu_edi_enable_nav_30(self):
        for wizard in self:
            enabled_moves = wizard.move_ids.filtered(lambda m: 'upload' in m._l10n_hu_edi_get_valid_actions())._origin
            wizard.l10n_hu_edi_enable_nav_30 = wizard.mode in ('invoice_single', 'invoice_multi') and enabled_moves

    @api.depends('l10n_hu_edi_enable_nav_30')
    def _compute_l10n_hu_edi_checkbox_nav_30(self):
        for wizard in self:
            wizard.l10n_hu_edi_checkbox_nav_30 = wizard.l10n_hu_edi_enable_nav_30

    @api.depends('l10n_hu_edi_enable_nav_30', 'l10n_hu_edi_checkbox_nav_30', 'move_ids')
    def _compute_l10n_hu_edi_actionable_errors(self):
        for wizard in self:
            if wizard.l10n_hu_edi_enable_nav_30:
                enabled_moves = wizard.move_ids.filtered(lambda m: 'upload' in m._l10n_hu_edi_get_valid_actions())._origin
                actionable_errors = enabled_moves._l10n_hu_edi_check_invoices()

                if enabled_moves and not wizard.l10n_hu_edi_checkbox_nav_30:
                    actionable_errors['checkbox_not_ticked'] = {
                        'message': _("Invoices issued in Hungary must, with few exceptions, be reported to the NAV's Online-Invoice system.")
                    }

                wizard.l10n_hu_edi_actionable_errors = actionable_errors

            else:
                wizard.l10n_hu_edi_actionable_errors = False

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _need_invoice_document(self, invoice):
        # EXTENDS 'account'
        # If the send & print triggers the NAV 3.0 flow, we want to re-generate the PDF.
        if invoice.country_code != 'HU':
            return super()._need_invoice_document(invoice)
        else:
            return invoice._l10n_hu_edi_get_valid_actions()

    @api.model
    def _prepare_invoice_pdf_report(self, invoice, invoice_data): 
        # EXTENDS 'account'
        # If we want to re-generate the PDF, we need to unlink the previous one.
        if invoice.country_code == 'HU':
            invoice.invoice_pdf_report_file = False
            invoice.invoice_pdf_report_id = False
        return super()._prepare_invoice_pdf_report(invoice, invoice_data)

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        invoices_hu = self.env['account.move'].browse([
            invoice.id
            for invoice, invoice_data in invoices_data.items()
            if invoice_data.get('l10n_hu_edi_checkbox_nav_30')
               and 'upload' in invoice._l10n_hu_edi_get_valid_actions()
        ])

        if not invoices_hu:
            return

        # Pre-emptively acquire write lock on all invoices to be processed
        # Otherwise, we will get a serialization error later
        # (bad, because Odoo will try to retry the entire request, leading to duplicate sending to NAV)
        invoices_hu._l10n_hu_edi_acquire_lock()

        # STEP 1: Generate and send the invoice XMLs.
        invoices_to_upload = invoices_hu.filtered(lambda m: 'upload' in m._l10n_hu_edi_get_valid_actions())

        # If we need to re-generate the PDF, break the link between the existing attachment and the 'invoice_pdf_report_file' field.
        # The existing PDF will remain linked to the invoice, but no longer as primary attachment.
        invoices_to_upload.invoice_pdf_report_id.write({'res_field': False})
        invoices_to_upload.invalidate_recordset(fnames=['invoice_pdf_report_id', 'invoice_pdf_report_file'])

        with L10nHuEdiConnection(self.env) as connection:
            invoices_to_upload._l10n_hu_edi_upload(connection)
            if self._can_commit():
                self.env.cr.commit()

            if any(m.l10n_hu_edi_state == 'sent' for m in invoices_hu):
                # If any invoices were just sent, wait so that NAV has enough time to process them
                time.sleep(2)

            # STEP 2: Query status
            invoices_hu.filtered(lambda m: 'query_status' in m._l10n_hu_edi_get_valid_actions())._l10n_hu_edi_query_status(connection)

        # STEP 3: Schedule update status of pending invoices in 10 minutes.
        if any(m.l10n_hu_edi_state not in [False, 'confirmed', 'confirmed_warning', 'rejected'] for m in invoices_hu):
            self.env.ref('l10n_hu_edi.ir_cron_update_status')._trigger(at=fields.Datetime.now() + timedelta(minutes=10))

        # STEP 4: Error / success handling.
        for invoice in invoices_hu:
            # Log outcome in chatter
            formatted_message = self._format_error_html(invoice.l10n_hu_edi_messages)
            invoice.with_context(no_new_invoice=True).message_post(body=formatted_message)

            # Update invoice_data with errors
            blocking_level = invoice.l10n_hu_edi_messages.get('blocking_level')
            if blocking_level == 'error':
                invoices_data[invoice]['error'] = invoice.l10n_hu_edi_messages

        if self._can_commit():
            self.env.cr.commit()

    @api.model
    def _l10n_hu_edi_cron_update_status(self):
        final_states = [False, 'confirmed', 'confirmed_warning', 'rejected', 'cancel_pending', 'cancelled']
        invoices_pending = self.env['account.move'].search([('l10n_hu_edi_state', 'not in', final_states)])
        invoices_pending.l10n_hu_edi_button_update_status(from_cron=True)

        if any(m.state not in final_states for m in invoices_pending):
            # Trigger cron again in 10 minutes.
            self.env.ref('l10n_hu_edi.ir_cron_update_status')._trigger(at=fields.Datetime.now() + timedelta(minutes=10))
