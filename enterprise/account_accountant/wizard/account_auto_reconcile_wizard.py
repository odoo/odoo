from datetime import date

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError


class AccountAutoReconcileWizard(models.TransientModel):
    """ This wizard is used to automatically reconcile account.move.line.
    It is accessible trough Accounting > Accounting tab > Actions > Auto-reconcile menuitem.
    """
    _name = 'account.auto.reconcile.wizard'
    _description = 'Account automatic reconciliation wizard'
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.Many2many(comodel_name='account.move.line')  # Amls from which we derive a preset for the wizard
    from_date = fields.Date(string='From')
    to_date = fields.Date(string='To', default=fields.Date.context_today, required=True)
    account_ids = fields.Many2many(
        comodel_name='account.account',
        string='Accounts',
        check_company=True,
        domain="[('reconcile', '=', True), ('deprecated', '=', False), ('account_type', '!=', 'off_balance')]",
    )
    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string='Partners',
        check_company=True,
        domain="[('company_id', 'in', (False, company_id)), '|', ('parent_id', '=', False), ('is_company', '=', True)]",
    )
    search_mode = fields.Selection(
        selection=[
            ('one_to_one', "Perfect Match"),
            ('zero_balance', "Clear Account"),
        ],
        string='Reconcile',
        required=True,
        default='one_to_one',
        help="Reconcile journal items with opposite balance or clear accounts with a zero balance",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        domain = self.env.context.get('domain')
        if 'line_ids' in fields_list and 'line_ids' not in res and domain:
            amls = self.env['account.move.line'].search(domain)
            if amls:
                # pre-configure the wizard
                res.update(self._get_default_wizard_values(amls))
                res['line_ids'] = [Command.set(amls.ids)]
        return res

    @api.model
    def _get_default_wizard_values(self, amls):
        """ Derive a preset configuration based on amls.
        For example if all amls have the same account_id we will set it in the wizard.
        :param amls: account move lines from which we will derive a preset
        :return: a dict with preset values
        """
        return {
            'account_ids': [Command.set(amls[0].account_id.ids)] if all(aml.account_id == amls[0].account_id for aml in amls) else [],
            'partner_ids': [Command.set(amls[0].partner_id.ids)] if all(aml.partner_id == amls[0].partner_id for aml in amls) else [],
            'search_mode': 'zero_balance' if amls.company_currency_id.is_zero(sum(amls.mapped('balance'))) else 'one_to_one',
            'from_date': min(amls.mapped('date')),
            'to_date': max(amls.mapped('date')),
        }

    def _get_wizard_values(self):
        """ Get the current configuration of the wizard as a dict of values.
        :return: a dict with the current configuration of the wizard.
        """
        self.ensure_one()
        return {
            'account_ids': [Command.set(self.account_ids.ids)] if self.account_ids else [],
            'partner_ids': [Command.set(self.partner_ids.ids)] if self.partner_ids else [],
            'search_mode': self.search_mode,
            'from_date': self.from_date,
            'to_date': self.to_date,
        }

    # ==== Business methods ====
    def _get_amls_domain(self):
        """ Get the domain of amls to be auto-reconciled. """
        self.ensure_one()
        if self.line_ids and self._get_wizard_values() == self._get_default_wizard_values(self.line_ids):
            domain = [('id', 'in', self.line_ids.ids)]
        else:
            domain = [
                ('company_id', '=', self.company_id.id),
                ('parent_state', '=', 'posted'),
                ('display_type', 'not in', ('line_section', 'line_note')),
                ('date', '>=', self.from_date or date.min),
                ('date', '<=', self.to_date),
                ('reconciled', '=', False),
                ('account_id.reconcile', '=', True),
                ('amount_residual_currency', '!=', 0.0),
                ('amount_residual', '!=', 0.0),  # excludes exchange difference lines
            ]
            if self.account_ids:
                domain.append(('account_id', 'in', self.account_ids.ids))
                if self.partner_ids:
                    domain.append(('partner_id', 'in', self.partner_ids.ids))
        return domain

    def _auto_reconcile_one_to_one(self):
        """ Auto-reconcile with one-to-one strategy:
        We will reconcile 2 amls together if their combined balance is zero.
        :return: a recordset of reconciled amls
        """
        grouped_amls_data = self.env['account.move.line']._read_group(
            self._get_amls_domain(),
            ['account_id', 'partner_id', 'currency_id', 'amount_residual_currency:abs_rounded'],
            ['id:recordset'],
        )
        all_reconciled_amls = self.env['account.move.line']
        amls_grouped_by_2 = []  # we need to group amls with right format for _reconcile_plan
        for *__, grouped_aml_ids in grouped_amls_data:
            positive_amls = grouped_aml_ids.filtered(lambda aml: aml.amount_residual_currency >= 0).sorted('date')
            negative_amls = (grouped_aml_ids - positive_amls).sorted('date')
            min_len = min(len(positive_amls), len(negative_amls))
            positive_amls = positive_amls[:min_len]
            negative_amls = negative_amls[:min_len]
            all_reconciled_amls += positive_amls + negative_amls
            amls_grouped_by_2 += [pos_aml + neg_aml for (pos_aml, neg_aml) in zip(positive_amls, negative_amls)]
        self.env['account.move.line']._reconcile_plan(amls_grouped_by_2)
        return all_reconciled_amls

    def _auto_reconcile_zero_balance(self):
        """ Auto-reconcile with zero balance strategy:
        We will reconcile all amls grouped by currency/account/partner that have a total balance of zero.
        :return: a recordset of reconciled amls
        """
        grouped_amls_data = self.env['account.move.line']._read_group(
            self._get_amls_domain(),
            groupby=['account_id', 'partner_id', 'currency_id'],
            aggregates=['id:recordset'],
            having=[('amount_residual_currency:sum_rounded', '=', 0)],
        )
        all_reconciled_amls = self.env['account.move.line']
        amls_grouped_together = []  # we need to group amls with right format for _reconcile_plan
        for aml_data in grouped_amls_data:
            all_reconciled_amls += aml_data[-1]
            amls_grouped_together += [aml_data[-1]]
        self.env['account.move.line']._reconcile_plan(amls_grouped_together)
        return all_reconciled_amls

    def auto_reconcile(self):
        """ Automatically reconcile amls given wizard's parameters.
        :return: an action that opens all reconciled items and related amls (exchange diff, etc)
        """
        self.ensure_one()
        if self.search_mode == 'zero_balance':
            reconciled_amls = self._auto_reconcile_zero_balance()
        else:
            # search_mode == 'one_to_one'
            reconciled_amls = self._auto_reconcile_one_to_one()
        reconciled_amls_and_related = self.env['account.move.line'].search([
            ('full_reconcile_id', 'in', reconciled_amls.full_reconcile_id.ids)
        ])
        if reconciled_amls_and_related:
            return {
                'name': _("Automatically Reconciled Entries"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move.line',
                'context': "{'search_default_group_by_matching': True}",
                'view_mode': 'list',
                'domain': [('id', 'in', reconciled_amls_and_related.ids)],
            }
        else:
            raise UserError("Nothing to reconcile.")
