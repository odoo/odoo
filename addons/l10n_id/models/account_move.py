# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz

from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Used to fetch the QR payment status.
    # List of dicts with the format: [{
    #     'qris_invoice_id': '13246',
    #     'qris_amount': 0.0,
    #     'qris_creation_datetime': '2024-02-27 03:00:00',
    #     'qris_content': 'xxx',
    # }]
    l10n_id_qris_invoice_details = fields.Json(
        string="QRIS Transaction Number",
        help="Transaction Number stored.",
        readonly=True,
        export_string_translation=False,
    )

    def _generate_qr_code(self, silent_errors=False):
        """
        Adds information about which invoice is triggering the creation of the QR-Code, so that we can link both together.
        """
        # EXTENDS account
        return super(
            AccountMove,
            self.with_context(qris_originating_invoice_id=self.id),
        )._generate_qr_code(silent_errors)

    def _l10n_id_cron_update_payment_status(self):
        """
        This cron will:
            - Get all invoices that are not paid, and have details about QRIS qr codes.
            - For each invoices, get information about the payment state of the QR using the API.
            - If the QR is not paid and it has been more than 30m, we discard that qr id (no longer valid)
            - If it is paid, we will register the payment on the invoices.
        """
        invoices = self.search([
            ('payment_state', '=', 'not_paid'),
            ('l10n_id_qris_invoice_details', '!=', False)
        ])
        return invoices._l10n_id_update_payment_status()

    def action_l10n_id_update_payment_status(self):
        """
        This action will:
            - Get all invoices that are not paid, and have details about QRIS qr codes.
            - For each invoices, get information about the payment state of the QR using the API.
            - If the QR is not paid and it has been more than 30m, we discard that qr id (no longer valid)
            - If it is paid, we will register the payment on the invoices.
        """
        invoices = self.filtered_domain([
            ('payment_state', '=', 'not_paid'),
            ('l10n_id_qris_invoice_details', '!=', False)
        ])
        return invoices._l10n_id_update_payment_status()

    def _l10n_id_update_payment_status(self):
        """ Starts by fetching the QR statuses for the invoices in self, then update said invoices based on the statuses """
        qr_statuses = self._l10n_id_get_qris_qr_statuses()
        return self._l10n_id_process_invoices(qr_statuses)

    def _l10n_id_get_qris_qr_statuses(self):
        """
        Query the API in order to get updated information on the status of each QR codes linked to the invoices in self.
        If the QR has been paid, only the paid information is returned.

        :return: a list with the format:
            {
                invoice: {
                    'paid': True,
                    'qr_statuses': [],
                },
                invoice: {
                    'paid': False,
                    'qr_statuses': [],
                }
            }
        """
        result = {}
        for invoice in self:
            paid = False
            unpaid_data = []
            paid_data = []
            # Looping to make requests is far from ideal, but we have no choices as they don't allow getting multiple QR result at once.
            # Ensure to loop in reverse and check from the most recent QR code.
            for qr_invoice in reversed(invoice.l10n_id_qris_invoice_details):
                status_response = invoice.partner_bank_id._l10n_id_qris_fetch_status(qr_invoice)
                if status_response['data'].get('qris_status') == 'paid':
                    paid_data.append(status_response['data'])
                    paid = True
                    break  # For paid invoices, we will only need the detail of the paid QR. The remaining will be discarded a bit later.
                else:
                    unpaid_data.append(status_response['data'])
            result[invoice.id] = {
                'paid': paid,
                'qr_statuses': paid_data if paid else unpaid_data,
            }
        return result

    def _l10n_id_process_invoices(self, invoices_statuses):
        """
        Receives the list of invoices and their statuses, and update them using it.
        For paid invoices we will register the payment and log a note, while for unpaid ones we will discard expired
        QR data and keep the non-expired ones for the next run.
        """
        jakarta_now = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Jakarta'), fields.Datetime.now())
        paid_invoices = self.env['account.move']
        paid_messages = {}
        for invoice in self:
            statuses = invoices_statuses.get(invoice.id)
            # Paid invoice: we simply prepare a message to notify of the payment with details if possible.
            if statuses['paid']:
                paid_status = statuses['qr_statuses'][0]
                if 'qris_payment_customername' in paid_status and 'qris_payment_methodby' in paid_status:
                    message = _(
                        "This invoice was paid by %(customer)s using QRIS with the payment method %(method)s.",
                        customer=paid_status['qris_payment_customername'],
                        method=paid_status['qris_payment_methodby'],
                    )
                else:
                    message = _("This invoice was paid using QRIS.")
                paid_invoices |= invoice
                paid_messages[invoice.id] = message
            # Unpaid invoices, we check the validity of the QR code and discard unneeded ones.
            else:
                qris_data_to_recheck = []
                for qr_invoice in invoice.l10n_id_qris_invoice_details:
                    # The QR date is in Jakarta time, so we ensure that we use correct timezones.
                    qris_datetime = fields.Datetime.to_datetime(
                        qr_invoice['qris_creation_datetime']
                    ).replace(tzinfo=pytz.timezone('Asia/Jakarta'))
                    # We will only reverify QR codes that have less than 30m of age, as after that they are no longer valid and will never be paid.
                    if (jakarta_now - qris_datetime).total_seconds() < 1800:
                        qris_data_to_recheck.append(qr_invoice)
                invoice.l10n_id_qris_invoice_details = qris_data_to_recheck

        # Update paid invoices
        if paid_invoices:
            paid_invoices._message_log_batch(bodies=paid_messages)
            paid_invoices.l10n_id_qris_invoice_details = False
            # Finally, register the payment:
            return self.env['account.payment.register'].with_context(
                active_model='account.move', active_ids=paid_invoices.ids
            ).create({'group_payment': False}).action_create_payments()
