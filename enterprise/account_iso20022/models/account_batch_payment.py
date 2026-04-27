# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import RedirectWarning, UserError

import base64
from datetime import datetime


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    iso20022_batch_booking = fields.Boolean(
        string="SCT Batch Booking",
        default=True,
        help="Request batch booking from the bank for the related bank statements.")

    iso20022_charge_bearer = fields.Selection(
        string="Charge Bearer",
        selection=[('CRED', 'Creditor'), ('DEBT', 'Debtor'), ('SLEV', 'Service Level'), ('SHAR', 'Shared')],
        compute='_compute_charge_bearer',
        readonly=False,
        store=True,
        help="Specifies which party/parties will bear the charges associated with the processing of the payment transaction."
    )

    @api.depends('payment_method_id')
    def _compute_charge_bearer(self):
        for record in self:
            if record.payment_method_id.code == 'sepa_ct':
                record.iso20022_charge_bearer = 'SLEV'
            else:
                record.iso20022_charge_bearer = 'SHAR'

    def _get_methods_generating_files(self):
        rslt = super()._get_methods_generating_files()
        rslt.extend(['sepa_ct', 'iso20022', 'iso20022_se', 'iso20022_ch'])
        return rslt

    def validate_batch(self):
        self.ensure_one()
        if self.payment_method_id.code == 'iso20022_se' and not self.env.company.iso20022_orgid_id:
            action = self.env.ref('account.action_account_config')
            raise RedirectWarning(
                message=_(
                    "The Name Identification and Issuer details are required to proceed. "
                    "Please configure them in the settings.",
                ),
                action=action.id,
                button_text=_('Go to settings'),
            )

        if self.payment_method_code and self.payment_method_code == 'sepa_ct':
            if self.journal_id.bank_account_id.acc_type != 'iban':
                raise RedirectWarning(
                    _(
                        "The bank account %(account)s, of journal '%(journal)s', is not of type IBAN.\nA valid IBAN account is required to use SEPA features.",
                        account=self.journal_id.bank_account_id.acc_number,
                        journal=self.journal_id.name,
                    ),
                    {
                        'view_mode': 'form',
                        'res_model': 'account.journal',
                        'type': 'ir.actions.act_window',
                        'res_id': self.journal_id.id,
                        'views': [[False, 'form']],
                    },
                    _("Configure Journal"),
                )
            if no_iban_payments := self.payment_ids.filtered(lambda x: x.partner_bank_id.acc_type != 'iban'):
                raise RedirectWarning(
                    _("The customer bank account set on some payments does not have an IBAN number. This is required for SEPA."),
                    no_iban_payments._get_records_action(name=_("Payments without IBAN")),
                    _("View Payments"),
                )
            if no_eur_payments := self.payment_ids.filtered(lambda x: x.currency_id.name != 'EUR'):
                raise RedirectWarning(
                    _("SEPA only accepts payments in EUR. Some payments are using another currency."),
                    no_eur_payments._get_records_action(name=_("Non-EUR Payments")),
                    _("View Payments"),
                )
        return super().validate_batch()

    def check_payments_for_errors(self):
        rslt = super().check_payments_for_errors()

        if self.payment_method_code not in ['sepa_ct', 'iso20022', 'iso20022_se', 'iso20022_ch']:
            return rslt

        no_bank_acc_payments = self.env['account.payment']
        too_big_payments = self.env['account.payment']

        amount_upper_bounds = {
            'sepa_ct': 999999999.99,
            'iso20022_ch': 9999999999.99,
        }
        for payment in self.payment_ids:
            if not payment.partner_bank_id:
                no_bank_acc_payments += payment

            amount_upper_bound = amount_upper_bounds.get(payment.payment_method_id.code, None)
            if amount_upper_bound and payment.currency_id.compare_amounts(payment.amount, amount_upper_bound) > 0:
                too_big_payments += payment

        if no_bank_acc_payments:
            rslt.append({'title': _("Some payments have no recipient bank account set."), 'records': no_bank_acc_payments})

        if too_big_payments:
            rslt.append({
                'title': _("Some payments are above the maximum amount allowed."),
                'records': too_big_payments,
            })

        return rslt

    def _generate_export_file(self):
        if self.payment_method_code in ['sepa_ct', 'iso20022', 'iso20022_se', 'iso20022_ch']:
            payments = self.payment_ids.sorted(key=lambda r: r.id)
            payment_dicts = self._generate_payment_template(payments)
            xml_doc = self.journal_id.create_iso20022_credit_transfer(
                payment_dicts,
                self.payment_method_code,
                batch_booking=self.iso20022_batch_booking,
                charge_bearer=self.iso20022_charge_bearer,
            )
            prefix = "SCT-" if self.payment_method_code == 'sepa_ct' else "PAIN-"
            return {
                'file': base64.encodebytes(xml_doc),
                'filename': "%s%s-%s.xml" % (prefix, self.journal_id.code, datetime.now().strftime('%Y%m%d%H%M%S')),
            }
        return super()._generate_export_file()

    def _get_payment_vals(self, payment):
        return {
            'id': payment.id,
            'name': str(payment.id) + '-' + (payment.memo or self.journal_id.code + '-' + str(fields.Date.today())),
            'payment_date': payment.date,
            'amount': payment.amount,
            'journal_id': self.journal_id.id,
            'currency_id': payment.currency_id.id,
            'payment_type': payment.payment_type,
            'memo': payment.memo,
            'partner_id': payment.partner_id.id,
            'partner_bank_id': payment.partner_bank_id.id,
            'partner_country_code': payment.partner_id.country_id.code,
            'iso20022_uetr': payment.iso20022_uetr,
        }

    def _generate_payment_template(self, payments):
        payment_dicts = []
        for payment in payments:
            if not payment.partner_bank_id:
                raise UserError(_('A bank account is not defined.'))
            payment_dicts.append(self._get_payment_vals(payment))
        return payment_dicts
