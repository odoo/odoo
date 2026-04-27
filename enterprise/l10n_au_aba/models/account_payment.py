# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError, RedirectWarning


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model
    def _get_method_codes_using_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_using_bank_account()
        res.append('aba_ct')
        return res

    @api.model
    def _get_method_codes_needing_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_needing_bank_account()
        res.append('aba_ct')
        return res

    @api.constrains('payment_method_line_id', 'journal_id', 'currency_id')
    def _l10n_au_aba_check_bank_account(self):
        aba_payment_method = self.env.ref('l10n_au_aba.account_payment_method_aba_ct')
        for rec in self:
            if rec.payment_method_id == aba_payment_method:
                bank_acc = rec.journal_id.bank_account_id
                if rec.currency_id.name != 'AUD':
                    raise ValidationError(_('ABA payments must be defined in AUD.'))
                if bank_acc.acc_type != 'aba' or not bank_acc.aba_bsb:
                    raise RedirectWarning(
                        message=_("Journal '%s' requires a proper ABA account. Please configure the Account first.", rec.journal_id.name),
                        action=rec.journal_id._get_records_action(name=_("Configure Journal"), target="new"),
                        button_text=_("Configure Journal")
                    )
                if not rec.journal_id.aba_user_spec or not rec.journal_id.aba_fic or not rec.journal_id.aba_user_number:
                    raise RedirectWarning(
                        message=_("ABA fields for account '%(account)s' on journal '%(journal)s' are not set. Please set the fields under ABA section!", account=bank_acc.acc_number, journal=rec.journal_id.name),
                        action=rec.journal_id._get_records_action(name=_("Configure Journal"), target="new"),
                        button_text=_("Configure Journal")
                    )

    @api.constrains('payment_method_line_id', 'partner_bank_id')
    def _check_partner_bank_account(self):
        aba_payment_method = self.env.ref('l10n_au_aba.account_payment_method_aba_ct')

        faulty_partners = self.filtered(lambda rec: rec.payment_method_id == aba_payment_method and (rec.partner_bank_id.acc_type != 'aba' or not rec.partner_bank_id.aba_bsb)).partner_id
        if faulty_partners:
            # Redirects to the contacts as some contacts may not have accounts set
            raise RedirectWarning(
                message=_("The Contact(s) requires a bank account with a valid BSB and account number. "
                          "Please configure the account(s) for the following Contact(s):\n%s", "\n".join(faulty_partners.mapped("display_name"))),
                action=faulty_partners._get_records_action(name=_("Configure Contact Account(s)"), target='new', views=[(False, "form"), (self.env.ref("l10n_au_aba.view_partner_tree").id, "list")]),
                button_text=_("Configure Contact Account(s)")
            )
