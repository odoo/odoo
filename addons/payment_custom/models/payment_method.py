from odoo import _, api, models


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    @api.model_create_multi
    def create(self, values_list):
        methods = super().create(values_list)
        methods.filtered(lambda m: m.code == 'wire_transfer').pending_msg = None
        return methods

    def action_recompute_pending_msg(self):
        """ Recompute the pending message to include the existing bank accounts. """
        account_payment_module = self.env['ir.module.module']._get('account_payment')
        if account_payment_module.state == 'installed':
            for method in self.filtered(lambda m: m.code == 'wire_transfer'):
                company_ids = method.provider_ids.mapped('company_id.id')
                accounts = self.env['account.journal']
                if len(set(company_ids)) == 1:
                    accounts = self.env['account.journal'].search([
                        *self.env['account.journal']._check_company_domain(company_ids[0]),
                        ('type', '=', 'bank'),
                    ]).bank_account_id
                account_names = "".join(f"<li><pre>{account.display_name}</pre></li>" for account in accounts)
                method.pending_msg = f'<div>' \
                                     f'<h5>{_("Please use the following transfer details")}</h5>' \
                                     f'<p><br></p>' \
                                     f'<h6>{_("Bank Account") if len(accounts) == 1 else _("Bank Accounts")}</h6>' \
                                     f'<ul>{account_names}</ul>' \
                                     f'<p><br></p>' \
                                     f'</div>'

    def _transfer_ensure_pending_msg_is_set(self):
        transfer_methods_without_msg = self.filtered(
            lambda m: m.code == 'wire_transfer' and not m.pending_msg
        )
        if transfer_methods_without_msg:
            transfer_methods_without_msg.action_recompute_pending_msg()
