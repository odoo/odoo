##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
from ast import literal_eval


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    checkbook_ids = fields.One2many('account.checkbook', 'journal_id', 'Checkbooks')

    @api.model
    def create(self, vals):
        rec = super(AccountJournal, self).create(vals)
        own_checks = self.env.ref('account_check.account_payment_method_new_own_checks')
        if (own_checks in rec.outbound_payment_method_ids and not rec.checkbook_ids):
            rec._create_checkbook()
        return rec

    def _create_checkbook(self):
        """ Create a checkbook for the journal """
        for rec in self:
            rec.checkbook_ids.create({'journal_id': rec.id, 'state': 'active'})

    @api.model
    def _enable_own_check_on_bank_journals(self):
        """ Enables Own Checks payment method
            Called upon module installation via data file.
        """
        domain = [('type', '=', 'bank')]
        force_company_id = self._context.get('force_company_id')
        if force_company_id:
            domain += [('company_id', '=', force_company_id)]
        bank_journals = self.search(domain)
        for bank_journal in bank_journals:
            if not bank_journal.checkbook_ids:
                bank_journal._create_checkbook()
            bank_journal.write({
                'outbound_payment_method_ids': [(4, self.env.ref('account_check.account_payment_method_new_own_checks').id, None)],
                'inbound_payment_method_ids': [
                    (4, self.env.ref('account_check.account_payment_method_in_own_checks').id, None),
                    # if we dont send default payment method is not computed and not added to journal
                    (4, self._default_inbound_payment_methods().id, None)],
            })

###############
# For dashboard
###############

    # def get_journal_dashboard_datas(self):
    #     domain_holding_third_checks = [
    #         ('type', '=', 'third_check'),
    #         ('journal_id', '=', self.id),
    #         ('state', '=', 'holding')
    #     ]
    #     domain_handed_own_checks = [
    #         ('type', '=', 'own_check'),
    #         ('journal_id', '=', self.id),
    #         ('state', '=', 'handed')
    #     ]
    #     handed_checks = self.env['account.check'].search(
    #         domain_handed_own_checks)
    #     holding_checks = self.env['account.check'].search(
    #         domain_holding_third_checks)

    #     num_checks_to_numerate = False
    #     if self.env['ir.actions.report'].search(
    #             [('report_name', '=', 'check_report')]):
    #         num_checks_to_numerate = self.env['account.payment'].search_count([
    #             ('journal_id', '=', self.id),
    #             ('payment_method_id.code', '=', 'own_check'),
    #             ('state', '=', 'draft'),
    #             ('check_name', '=', False),
    #         ])
    #     return dict(
    #         super(AccountJournal, self).get_journal_dashboard_datas(),
    #         num_checks_to_numerate=num_checks_to_numerate,
    #         num_holding_third_checks=len(holding_checks),
    #         show_third_checks=(
    #             'received_third_check' in
    #             self.inbound_payment_method_ids.mapped('code')),
    #         show_own_checks=(
    #             'own_check' in
    #             self.outbound_payment_method_ids.mapped('code')),
    #         num_handed_own_checks=len(handed_checks),
    #         handed_amount=formatLang(
    #             self.env, sum(handed_checks.mapped('amount_company_currency')),
    #             currency_obj=self.company_id.currency_id),
    #         holding_amount=formatLang(
    #             self.env, sum(holding_checks.mapped(
    #                 'amount_company_currency')),
    #             currency_obj=self.company_id.currency_id),
    #     )

    # def open_action_checks(self):
    #     check_type = self.env.context.get('check_type', False)
    #     if check_type == 'third_check':
    #         action_name = 'account_check.action_third_check'
    #     elif check_type == 'own_check':
    #         action_name = 'account_check.action_own_check'
    #     else:
    #         return False
    #     actions = self.env.ref(action_name)
    #     action_read = actions.read()[0]
    #     context = literal_eval(action_read['context'])
    #     context['search_default_journal_id'] = self.id
    #     action_read['context'] = context
    #     return action_read

    # def action_checks_to_numerate(self):
    #     return {
    #         'name': _('Checks to Print and Numerate'),
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'list,form,graph',
    #         'res_model': 'account.payment',
    #         'context': dict(
    #             self.env.context,
    #             search_default_checks_to_numerate=1,
    #             search_default_journal_id=self.id,
    #             journal_id=self.id,
    #             default_journal_id=self.id,
    #             default_payment_type='outbound',
    #             default_payment_method_id=self.env.ref(
    #                 'account_check.account_payment_method_own_check').id,
    #         ),
    #     }
