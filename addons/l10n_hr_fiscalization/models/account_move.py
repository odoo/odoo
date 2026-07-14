from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_hr_fiscalization_jir = fields.Char(string="JIR", help="Unique identifier of the invoice (JIR)", readonly=True)
    l10n_hr_fiscalization_zki = fields.Char(string="ZKI", help="Protective code of the issuer (ZKI)", readonly=True)
    l10n_hr_fiscalization_old_recipient_oib = fields.Char(string="Old Personal OIB")
    l10n_hr_old_payment_method_type = fields.Char(string="Old Payment Method")
    l10n_hr_fiscalization_payment_method_change_date = fields.Datetime(string="Payment Method Change Date", readonly=True)

    @api.ondelete(at_uninstall=False)
    def _l10n_hr_fiscalization_unlink_except_fiscalized(self):
        if not self.env.context.get('force_delete') and any(m.l10n_hr_fiscalization_status == '0' for m in self):
            raise UserError(self.env._('You cannot delete a move that has been fiscalized.'))

    def _l10n_hr_get_fiscalization_qr_code(self):
        """Generate the Croatian fiscalization QR URL.

        Spec per Croatian TA:
        - Base URL: https://porezna.gov.hr/rn
        - Identifiers: use JIR if present, otherwise ZKI
        - Datetime format: YYYYMMDD_HHMM (issuance datetime)
        - Amount: absolute total with two decimals, period removed

        Uses `l10n_hr_invoice_sending_time` (issuance datetime) for QR; The datetime is
        converted to the Croatian timezone (Europe/Zagreb) for consistent
        representation with TA.
        """
        self.ensure_one()

        identifier = self.l10n_hr_fiscalization_jir or self.l10n_hr_fiscalization_zki
        datetime_source = self.l10n_hr_invoice_sending_time
        if not identifier or not datetime_source:
            return None

        dt_local = self.env['account.move.send']._l10n_hr_to_hr_local_dt(datetime_source)
        formatted_date = dt_local.strftime('%Y%m%d_%H%M')

        amount_str = f'{self.amount_total_signed:.2f}'.replace('.', '')

        base_url = 'https://porezna.gov.hr/rn'
        if self.l10n_hr_fiscalization_jir:
            return f"{base_url}?jir={self.l10n_hr_fiscalization_jir}&datv={formatted_date}&izn={amount_str}"
        return f"{base_url}?zki={self.l10n_hr_fiscalization_zki}&datv={formatted_date}&izn={amount_str}"

    def _l10n_hr_change_payment_method(self, new_payment_method, new_recipient_oib=None, change_oib=False):
        """Change payment method and/or recipient OIB for a fiscalized invoice via TA API.

        Uses the EDI send wizard plumbing to build, sign, and send a
        dedicated ChangePaymentMethod request. Updates the invoice on success.

        Args:
            new_payment_method: New payment method code (G, K, T, O)
            new_recipient_oib: New recipient OIB (11 digits) or empty string to clear
            change_oib: Boolean indicating if OIB should be changed
        """
        self.ensure_one()
        _ = self.env._

        if self.l10n_hr_fiscalization_status != '0' or not self.l10n_hr_fiscalization_jir:
            return {
                'success': False,
                'message': _("Only fiscalized invoices can have their data changed.")
            }

        fiscalization_date = fields.Date.context_today(self, self.l10n_hr_invoice_sending_time)
        today = fields.Date.context_today(self)
        if fiscalization_date != today:
            return {
                'success': False,
                'message': _("Invoice data can only be changed on the same day the invoice was fiscalized.")
            }

        if new_payment_method == 'T' and change_oib and new_recipient_oib:
            return {
                'success': False,
                'message': _("Recipient OIB cannot be sent with payment method 'Transakcijski račun' (T).")
            }

        try:
            send_wizard = self.action_invoice_sent()
            send_obj = self.env[send_wizard['res_model']].with_context(send_wizard['context']).create({})
            request_data = send_obj._l10n_hr_prepare_fiscalization_request(self)
            request_data['changed_payment_method'] = new_payment_method

            message = f"Payment method type have been changed to {new_payment_method} "
            if change_oib:
                request_data['changed_recipient_oib'] = new_recipient_oib if new_recipient_oib else ''
                request_data['change_oib'] = True
                message = f"Recipient OIB have been changed to {new_recipient_oib}!"

            xml_doc = send_obj._l10n_hr_generate_xml_file(request_data, is_payment_change=True)
            response = send_obj._l10n_hr_send_xml_file(xml_doc, is_payment_change=True)

            if response.get('success'):
                self.l10n_hr_payment_method_type = new_payment_method

                if response.get('datetime_of_payment_method_change'):
                    change_datetime = send_obj._l10n_hr_datetime_to_odoo(response.get('datetime_of_payment_method_change'))
                    self.l10n_hr_fiscalization_payment_method_change_date = change_datetime
                return {
                    'success': True,
                    'message': message,
                }
            else:
                return {
                    'success': False,
                    'message': response.get('error'),
                }
        except Exception as e:  # noqa: BLE001
            return {
                'success': False,
                'message': str(e)
            }

    def _l10n_hr_check_fiscalization_status(self):
        self.ensure_one()
        _ = self.env._

        if self.l10n_hr_fiscalization_status != '0' and not self.l10n_hr_fiscalization_jir:
            return {
                'success': False,
                'message': _("Only fiscalized invoices can be checked. Send invoice to Fiscalization first.")
            }

        try:
            send_wizard = self.action_invoice_sent()
            send_obj = self.env[send_wizard['res_model']].with_context(send_wizard['context']).create({})
            if not self.l10n_hr_fiscalization_zki:
                self.l10n_hr_fiscalization_zki = send_obj._l10n_hr_generate_zki(self)
            request_data = send_obj._l10n_hr_prepare_fiscalization_request(self)
            xml_doc = send_obj._l10n_hr_generate_xml_file(request_data, check_status=True)
            response = send_obj._l10n_hr_send_xml_file(xml_doc, check_status=True)

            if response['success']:
                return {
                    'success': True,
                    'message': _("Invoice is properly fiscalized."),
                    'invoice_details': response.get('invoice_details', {})
                }
            else:
                return {
                    'success': False,
                    'message': _("Fiscalization check failed: %s", response.get('error')),
                    'invoice_details': response.get('invoice_details', {})
                }
        except Exception as e:  # noqa: BLE001
            return {
                'success': False,
                'message': _("Fiscalization check failed: %s", e),
                'details': [],
                'invoice_details': {}
            }

    def action_check_fiscalization_status(self):
        self.ensure_one()
        result = self._l10n_hr_check_fiscalization_status()

        message = result['message']
        if result.get('details'):
            detail_messages = []
            for detail in result['details']:
                if isinstance(detail, dict) and 'code' in detail and 'message' in detail:
                    detail_messages.append(f"{detail['code']}: {detail['message']}")

            if detail_messages:
                message += "\n\nDetails:\n" + "\n".join(detail_messages)

        if not result['success'] and result.get('invoice_details'):
            invoice_details = result.get('invoice_details', {})
            if invoice_details:
                message += "\n\nInvoice Details from Tax Authority:\n"
                for key, value in invoice_details.items():
                    if isinstance(value, (dict, list)):
                        message += f"{key}: {value!s}\n"
                    else:
                        message += f"{key}: {value}\n"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._('Fiscalization Status Check'),
                'message': message,
                'type': 'success' if result['success'] else 'danger',
            }
        }
