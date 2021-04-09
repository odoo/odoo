##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    rejected_check_account_id = fields.Many2one(
        'account.account.template',
        'Rejected Check Account',
        help='Rejection Checks account, for eg. "Rejected Checks"',
        # domain=[('type', 'in', ['other'])],
    )
    deferred_check_account_id = fields.Many2one(
        'account.account.template',
        'Deferred Check Account',
        help='Deferred Checks account, for eg. "Deferred Checks"',
        # domain=[('type', 'in', ['other'])],
    )
    holding_check_account_id = fields.Many2one(
        'account.account.template',
        'Holding Check Account',
        help='Holding Checks account for third checks, '
        'for eg. "Holding Checks"',
        # domain=[('type', 'in', ['other'])],
    )

    def _load_template(self, company, code_digits=None, account_ref=None, taxes_ref=None):
        account_ref, taxes_ref = super()._load_template(
            company, code_digits=code_digits, account_ref=account_ref, taxes_ref=taxes_ref)
        for field in [
                'rejected_check_account_id',
                'deferred_check_account_id',
                'holding_check_account_id']:
            account_field = self[field]
            # TODO we should send it in the context and overwrite with
            # lower hierichy values
            if account_field:
                company[field] = account_ref[account_field.id]
        return account_ref, taxes_ref

    def _create_bank_journals(self, company, acc_template_ref):
        """
        Bank - Cash journals are created with this method
        Inherit this function in order to add checks to cash and bank
        journals. This is because usually will be installed before chart loaded
        and they will be disable by default
        """

        res = super(
            AccountChartTemplate, self)._create_bank_journals(
            company, acc_template_ref)

        # creamos diario para cheques de terceros
        received_third_check = self.env.ref(
            'account_check.account_payment_method_received_third_check')
        delivered_third_check = self.env.ref(
            'account_check.account_payment_method_delivered_third_check')
        self.env['account.journal'].create({
            'name': 'Cheques de Terceros',
            'type': 'cash',
            'company_id': company.id,
            'inbound_payment_method_ids': [
                (4, received_third_check.id, None)],
            'outbound_payment_method_ids': [
                (4, delivered_third_check.id, None)],
        })

        self.env['account.journal'].with_context(
            force_company_id=company.id)._enable_issue_check_on_bank_journals()
        return res
