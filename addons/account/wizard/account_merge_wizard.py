from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError
from odoo.tools import SQL


class AccountMergeWizard(models.TransientModel):
    _name = 'account.merge.wizard'
    _description = "Account merge wizard"

    account_ids = fields.Many2many('account.account')
    is_group_by_name = fields.Boolean(
        string="Group by name?",
        default=False,
        help="Tick this checkbox if you want accounts to be grouped by name for merging."
    )
    wizard_line_ids = fields.One2many(
        comodel_name='account.merge.wizard.line',
        inverse_name='wizard_id',
        compute='_compute_wizard_line_ids',
        store=True,
        readonly=False,
    )
    disable_merge_button = fields.Boolean(compute='_compute_disable_merge_button')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not set(fields) & {'account_ids', 'wizard_line_ids'} or set(res.keys()) & {'account_ids', 'wizard_line_ids'}:
            return res

        if self.env.context.get('active_model') != 'account.account':
            raise UserError(_("This can only be used on accounts."))
        if len(self.env.context.get('active_ids') or []) < 2:
            raise UserError(_("You must select at least 2 accounts."))

        res['account_ids'] = [Command.set(self.env.context.get('active_ids'))]
        return res

    def _get_grouping_key(self, account):
        """ Return a grouping key for the given account. """
        self.ensure_one()
        grouping_fields = ['account_type', 'non_trade', 'currency_id', 'reconcile', 'deprecated']
        if self.is_group_by_name:
            grouping_fields.append('name')
        return tuple(account[field] for field in grouping_fields)

    @api.depends('is_group_by_name', 'account_ids')
    def _compute_wizard_line_ids(self):
        """ Determine which accounts to merge together. """
        for wizard in self:
            # Filter out Bank / Cash accounts
            accounts = wizard.account_ids._origin.filtered(lambda a: a.account_type not in ('asset_bank', 'asset_cash'))

            wizard_lines_vals_list = []
            sequence = 0
            for grouping_key, group_accounts in accounts.grouped(wizard._get_grouping_key).items():
                grouping_key_str = str(grouping_key)
                wizard_lines_vals_list.append({
                    'display_type': 'line_section',
                    'grouping_key': grouping_key_str,
                    'sequence': (sequence := sequence + 1),
                    'account_id': group_accounts[0].id  # Used to compute the group name
                })
                for account in group_accounts:
                    wizard_lines_vals_list.append({
                        'display_type': 'account',
                        'account_id': account.id,
                        'grouping_key': grouping_key_str,
                        'is_selected': True,
                        'sequence': (sequence := sequence + 1),
                    })

            wizard.wizard_line_ids = [Command.clear()] + [
                Command.create(vals)
                for vals in wizard_lines_vals_list
            ]

    @api.depends('wizard_line_ids.is_selected', 'wizard_line_ids.info')
    def _compute_disable_merge_button(self):
        for wizard in self:
            wizard_lines_to_merge = wizard.wizard_line_ids.filtered(lambda l: l.display_type == 'account' and l.is_selected and not l.info)
            wizard.disable_merge_button = all(
                len(wizard_line_group) < 2
                for wizard_line_group in wizard_lines_to_merge.grouped('grouping_key').values()
            )

    def _get_window_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Merge Accounts"),
            'view_id': self.env.ref('account.account_merge_wizard_form').id,
            'context': self.env.context,
            'res_model': 'account.merge.wizard',
            'res_id': self.id,
            'target': 'new',
            'view_mode': 'form',
        }

    def action_merge(self):
        """ Merge each group of accounts in `self.wizard_line_ids`. """
        self._check_access_rights(self.account_ids)

        for wizard in self:
            wizard_lines_selected = wizard.wizard_line_ids.filtered(lambda l: l.display_type == 'account' and l.is_selected and not l.info)
            for wizard_lines_group in wizard_lines_selected.grouped('grouping_key').values():
                if len(wizard_lines_group) > 1:
                    # This ensures that if one account in the group has hashed entries, it appears first, ensuring
                    # that its ID doesn't get changed by the merge.
                    self._action_merge(wizard_lines_group.sorted('account_has_hashed_entries', reverse=True).account_id)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("Accounts successfully merged!"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    @api.model
    def _check_access_rights(self, accounts):
        accounts.check_access('write')
        if forbidden_companies := (accounts.sudo().company_ids - self.env.user.company_ids):
            raise UserError(_(
                "You do not have the right to perform this operation as you do not have access to the following companies: %s.",
                ", ".join(c.name for c in forbidden_companies)
            ))

    @api.model
    def _action_merge(self, accounts):
        """ Merge `accounts`:
            - the first account is extended to each company of the others, keeping their codes and names;
            - the others are deleted; and
            - journal items and other references are retargeted to the first account.
        """
        # Step 1: Keep track of the company_ids and codes we should write on the account.
        # We will do so only at the end, to avoid triggering the constraint that prevents duplicate codes.
        company_ids_to_write = accounts.sudo().company_ids
        code_by_company = {}
        all_root_companies = self.env['res.company'].sudo().search([('parent_id', '=', False)])
        for account in accounts:
            for company in account.company_ids & all_root_companies:
                code_by_company[company] = account.with_company(company).sudo().code
            for company in all_root_companies - account.company_ids:
                if code := account.with_company(company).sudo().code:
                    code_by_company[company] = code

        account_to_merge_into = accounts[0]
        accounts_to_remove = accounts[1:]

        # Step 2: Check that we have write access to all the accounts and access to all the companies
        # of these accounts.
        self._check_access_rights(accounts)

        # Step 3: Update records in DB.
        # 3.1: Update foreign keys in DB
        wiz = self.env['base.partner.merge.automatic.wizard'].new()
        wiz._update_foreign_keys_generic('account.account', accounts_to_remove, account_to_merge_into)

        # 3.2: Update Reference and Many2OneReference fields that reference account.account
        wiz._update_reference_fields_generic('account.account', accounts_to_remove, account_to_merge_into)

        # Step 4: Remove merged accounts
        self.env.invalidate_all()
        self.env.cr.execute(SQL(
            """
             DELETE FROM account_account
              WHERE id IN %(account_ids_to_delete)s
            """,
            account_ids_to_delete=tuple(accounts_to_remove.ids),
        ))

        # Clear ir.model.data ormcache
        self.env.registry.clear_cache()

        # Step 5: Write company_ids and codes on the account
        for company, code in code_by_company.items():
            account_to_merge_into.with_company(company).sudo().code = code

        account_to_merge_into.sudo().company_ids = company_ids_to_write


class AccountMergeWizardLine(models.TransientModel):
    _name = 'account.merge.wizard.line'
    _description = "Account merge wizard line"
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        comodel_name='account.merge.wizard',
        required=True,
        ondelete='cascade',
    )
    grouping_key = fields.Char()
    sequence = fields.Integer()
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('account', "Account"),
        ],
        required=True,
    )
    is_selected = fields.Boolean()
    account_id = fields.Many2one(
        string="Account",
        comodel_name='account.account',
        ondelete='cascade',
        readonly=True,
    )
    company_ids = fields.Many2many(
        string="Companies",
        related='account_id.company_ids',
    )
    info = fields.Char(
        string='Info',
        compute='_compute_info',
        help="Contains either the section name or error message, depending on the line type."
    )
    account_has_hashed_entries = fields.Boolean(compute='_compute_account_has_hashed_entries')

    @api.depends('account_id')
    def _compute_account_has_hashed_entries(self):
        # optimization to avoid having to re-check which accounts have hashed entries
        query = self.env['account.move.line']._where_calc([
            ('account_id', 'in', self.account_id.ids),
            ('move_id.inalterable_hash', '!=', False),
        ])
        query_result = self.env.execute_query(query.select(SQL('DISTINCT account_move_line.account_id')))
        accounts_with_hashed_entries_ids = {r[0] for r in query_result}
        wizard_lines_with_hashed_entries = self.filtered(lambda l: l.account_id.id in accounts_with_hashed_entries_ids)
        wizard_lines_with_hashed_entries.account_has_hashed_entries = True
        (self - wizard_lines_with_hashed_entries).account_has_hashed_entries = False

    @api.depends('account_id', 'wizard_id.wizard_line_ids.is_selected', 'display_type')
    def _compute_info(self):
        """ This re-computes the error message for each wizard line every time the user selects or deselects a wizard line.

        In reality accounts will only affect the mergeability of other accounts in the same merge group.
        Therefore this method delegates the logic of determining whether an account can be merged to
        `_apply_different_companies_constraint` and `_apply_hashed_moves_constraint` which work on a merge group basis.
        """
        for wizard_line in self.filtered(lambda l: l.display_type == 'line_section'):
            wizard_line.info = wizard_line._get_group_name()
        for wizard_line_group in self.filtered(lambda l: l.display_type == 'account').grouped(lambda l: (l.wizard_id, l.grouping_key)).values():
            # Reset the error messages for the wizard lines in the group to False, then
            # re-compute them for the whole group.
            wizard_line_group.info = False
            wizard_line_group._apply_different_companies_constraint()
            wizard_line_group._apply_hashed_moves_constraint()

    def _get_group_name(self):
        """ Return a human-readable name for a wizard line's group, based on its `account_id`, in the format:
        '{Trade/Non-trade} Receivable {USD} {Reconcilable} {Deprecated}'
        """
        self.ensure_one()

        account_type_label = dict(self.pool['account.account'].account_type._description_selection(self.env))[self.account_id.account_type]
        if self.account_id.account_type in ['asset_receivable', 'liability_payable']:
            account_type_label = _("Non-trade %s", account_type_label) if self.account_id.non_trade else _("Trade %s", account_type_label)

        other_name_elements = []
        if self.account_id.currency_id:
            other_name_elements.append(self.account_id.currency_id.name)

        if self.account_id.reconcile:
            other_name_elements.append(_("Reconcilable"))

        if self.account_id.deprecated:
            other_name_elements.append(_("Deprecated"))

        if not self.wizard_id.is_group_by_name:
            grouping_key_name = account_type_label
            if other_name_elements:
                grouping_key_name = f'{grouping_key_name} ({", ".join(other_name_elements)})'
        else:
            grouping_key_name = f'{self.account_id.name} ({", ".join([account_type_label] + other_name_elements)})'

        return grouping_key_name

    def _apply_different_companies_constraint(self):
        """ Set `info` on wizard lines if an account cannot be merged
            because it belongs to the same company as another account.

            If users want to do that, they should mass-edit the account on the journal items.

            The wizard lines in `self` should have the same `grouping_key`.
        """
        companies_seen = self.env['res.company']
        account_belonging_to_company = {}
        for wizard_line in self:
            if wizard_line.is_selected and not wizard_line.info:
                if shared_companies := (wizard_line.company_ids & companies_seen):
                    wizard_line.info = _(
                        "Belongs to the same company as %s.",
                        account_belonging_to_company[shared_companies[0]].display_name
                    )
                else:
                    companies_seen |= wizard_line.company_ids
                    for company in wizard_line.company_ids:
                        if company not in account_belonging_to_company:
                            account_belonging_to_company[company] = wizard_line.account_id

    def _apply_hashed_moves_constraint(self):
        """ Set `info` on wizard lines if an account cannot be merged because it
            has hashed entries.

            If there are hashed entries in an account, then the merge must preserve that account's ID.
            So we cannot merge two accounts that contain hashed entries.

            The wizard lines in `self` should have the same `grouping_key`.
        """
        account_to_merge_into = None
        for wizard_line in self:
            if wizard_line.is_selected and not wizard_line.info and wizard_line.account_has_hashed_entries:
                if not account_to_merge_into:
                    account_to_merge_into = wizard_line.account_id
                else:
                    wizard_line.info = _(
                        "Contains hashed entries, but %s also has hashed entries.",
                        account_to_merge_into.display_name
                    )
