# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_id_qris_transaction_ids = fields.Many2many('l10n_id.qris.transaction')

    def _generate_qr_code(self, silent_errors=False):
        """
        Adds information about which invoice is triggering the creation of the QR-Code, so that we can link both together.
        """
        # EXTENDS account
        return super(
            AccountMove,
            self.with_context(qris_model="account.move", qris_model_id=str(self.id)),
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
            ('l10n_id_qris_transaction_ids', '!=', False)
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
            ('l10n_id_qris_transaction_ids', '!=', False)
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
            result[invoice.id] = invoice.l10n_id_qris_transaction_ids._l10n_id_get_qris_qr_statuses()
        return result

    def _l10n_id_process_invoices(self, invoices_statuses):
        """
        Receives the list of invoices and their statuses, and update them using it.
        For paid invoices we will register the payment and log a note, while for unpaid ones we will discard expired
        QR data and keep the non-expired ones for the next run.
        """
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

        # Update paid invoices
        if paid_invoices:
            paid_invoices._message_log_batch(bodies=paid_messages)
            # Finally, register the payment:
            return self.env['account.payment.register'].with_context(
                active_model='account.move', active_ids=paid_invoices.ids
            ).create({'group_payment': False}).action_create_payments()

    def _compute_tax_totals(self):
        """ OVERRIDE

        For invoices based on ID company as of January 2025, there is a separate tax base computation for non-luxury goods.
        Tax base is supposed to be 11/12 of original while tax amount is increased from 11% to 12% hence effectively
        maintaining 11% tax amount.

        We change tax totals section to display adjusted base amount on invoice PDF for special non-luxury goods tax group.
        """
        super()._compute_tax_totals()
        for move in self.filtered(lambda m: m.is_sale_document()):
            # invoice might be coming from different companies, each tax group with unique XML ID
            non_luxury_tax_group = self.env['account.chart.template'].with_company(move.company_id.id).ref("l10n_id_tax_group_non_luxury_goods", raise_if_not_found=False)

            if not non_luxury_tax_group or move.invoice_date and move.invoice_date < fields.Date.to_date('2025-01-01'):
                continue

            # for every tax group component with non-luxury tax group, we adjust the base amount and adjust the display to
            # show base amount
            change_tax_base = False
            for subtotal in move.tax_totals["subtotals"]:
                for tax_group in subtotal["tax_groups"]:
                    if tax_group["id"] == non_luxury_tax_group.id:
                        tax_group.update({
                            "display_base_amount": tax_group["display_base_amount"] * (11 / 12),
                            "display_base_amount_currency": tax_group["display_base_amount_currency"] * (11 / 12),
                            "group_name": tax_group["group_name"] + " (on DPP)",
                        })
                        change_tax_base = True
            if change_tax_base:
                move.tax_totals["same_tax_base"] = False
