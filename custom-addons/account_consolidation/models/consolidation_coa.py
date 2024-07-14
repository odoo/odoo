# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import ValidationError


class ConsolidationChart(models.Model):
    _name = "consolidation.chart"
    _description = "Consolidation chart"

    name = fields.Char(string='Consolidation Name', required=True)
    currency_id = fields.Many2one('res.currency', string="Target Currency", required=True)
    period_ids = fields.One2many('consolidation.period', 'chart_id', string="Analysis Periods")
    period_ids_count = fields.Integer(compute='_compute_period_ids_count', string='# Periods')
    account_ids = fields.One2many('consolidation.account', 'chart_id', 'Consolidation Accounts')
    account_ids_count = fields.Integer(compute='_compute_account_ids_count', string='# Accounts')
    group_ids = fields.One2many('consolidation.group', 'chart_id', 'Account Groups')
    group_ids_count = fields.Integer(compute='_compute_group_ids_count', string='# Groups')
    rate_ids = fields.One2many('consolidation.rate', 'chart_id', 'Consolidation Rates')

    color = fields.Integer('Color Index', help='Used in the kanban view', default=0)
    company_ids = fields.Many2many('res.company', string="Companies")
    children_ids = fields.Many2many('consolidation.chart', 'account_consolidation_inner_rel', 'children_ids',
                                    'parent_ids', string="Sub-consolidations")
    parents_ids = fields.Many2many('consolidation.chart', 'account_consolidation_inner_rel', 'parent_ids',
                                   'children_ids', string="Consolidated In")
    invert_sign = fields.Boolean('Invert Balance Sign', default=False)
    sign = fields.Integer(compute='_compute_sign')

    # COMPUTEDS
    @api.depends('account_ids')
    def _compute_account_ids_count(self):
        """
        Compute the amount of consolidation accounts are linked to this chart.
        """
        for record in self:
            record.account_ids_count = len(record.account_ids)

    @api.depends('group_ids')
    def _compute_group_ids_count(self):
        """
        Compute the amount of consolidation account sections are linked to this chart.
        """
        for record in self:
            record.group_ids_count = len(record.group_ids)

    @api.depends('period_ids')
    def _compute_period_ids_count(self):
        """
        Compute the amount of analysis periods are linked to this chart.
        """
        for record in self:
            record.period_ids_count = len(record.period_ids)

    @api.depends('invert_sign')
    def _compute_sign(self):
        for chart in self:
            chart.sign = -1 if chart.invert_sign else 1

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = self.name + ' (copy)'
        default['color'] = ((self.color if self.color else 0) + 1) % 12
        default['group_ids'] = [group.copy().id for group in self.group_ids if not group.parent_id]  # This will copy parent groups, which will automatically copy child groups.
        # Copy accounts not linked to a group. Accounts linked to a group are handled in the group copy.
        default['account_ids'] = [account.copy().id for account in self.account_ids if not account.group_id]
        res = super().copy(default)
        # Link the automatically copied children to the new chart.
        res.group_ids.child_ids._init_recursive_group_chart(res.id)
        # We copied the groups, which copied the accounts. We still need to link the new accounts with the chart.
        res.group_ids.account_ids.chart_id = res.id
        return res

    # ACTIONS

    def action_open_mapping(self):
        """
        Open mapping view for this chart.
        :return: the action to execute
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'consolidation.account',
            'view_mode': 'tree',
            'views': [[self.env.ref('account_consolidation.consolidation_account_tree_mapping').id, 'list']],
            'domain': [('chart_id', '=', self.id)],
            'context': {},
            'name': _('Account Mapping: %(chart)s', chart=self.name),
            'search_view_id': [self.env.ref('account_consolidation.consolidation_account_search_mapping').id, 'search']
        }

    # ONBOARDING
    @api.model
    # Onboarding requires an object method
    def setting_consolidation_action(self):
        """
        Called by the 'Create' button of the setup bar in "first consolidation" step.
        :return: the action to execute
        """
        action = self.env["ir.actions.actions"]._for_xml_id("account_consolidation.consolidation_chart_action_onboarding")
        last_chart = self.search([], order="id desc", limit=1)
        if last_chart.id:
            action.update({
                'res_id': last_chart.id,
            })
        return action

    def action_save_onboarding_consolidation_step(self):
        self.env['onboarding.onboarding.step'].action_validate_step(
            'account_consolidation.onboarding_onboarding_step_setup_consolidation'
        )

    @api.model
    def setting_consolidated_chart_of_accounts_action(self):
        """
        Called by the 'Setup' button of the setup bar in "Consolidated Chart of Accounts" step.
        :return: the action to execute
        """
        action = self.env["ir.actions.actions"]._for_xml_id("account_consolidation.consolidation_account_action")
        last_chart = self.search([], order="id desc", limit=1)
        action.update({
            'context': {'default_chart_id': last_chart.id, 'search_default_chart_id': last_chart.id},
            'views': [
                (self.env.ref('account_consolidation.consolidation_account_tree_onboarding').id, 'list'),
                (False, 'form')
            ]
        })
        self.env['onboarding.onboarding.step'].action_validate_step(
            'account_consolidation.onboarding_onboarding_step_setup_ccoa'
        )
        return action

    @api.model
    def setting_create_period_action(self):
        """
        Called by the 'Create' button of the setup bar in "first period" step.
        :return: the action to execute
        """
        action = self.env["ir.actions.actions"]._for_xml_id("account_consolidation.consolidation_period_action_onboarding")
        last_chart = self.search([], order="id desc", limit=1)
        action.update({'context': {'default_chart_id': last_chart.id}})
        return action


class ConsolidationAccount(models.Model):
    _name = "consolidation.account"
    _description = "Consolidation account"
    _order = 'sequence asc, id'
    _rec_name = 'name'

    def get_default_chart_id(self):
        return self.env['consolidation.chart'].search([], order="id desc", limit=1)

    chart_id = fields.Many2one('consolidation.chart', string="Consolidation", ondelete="cascade", required=True,
                               default=get_default_chart_id)
    name = fields.Char(string='Name', required=True)
    code = fields.Char(size=64, required=False, index=True, copy=False)
    full_name = fields.Char(string='Full Name', compute='_compute_full_name')
    sequence = fields.Integer()

    group_id = fields.Many2one('consolidation.group', string='Group')
    account_ids = fields.Many2many('account.account', string="Accounts")
    currency_mode = fields.Selection([('end', 'Closing Rate'), ('avg', 'Average Rate'), ('hist', 'Historical Rate')],
                                     required=True, default='end', string='Currency Conversion Method')
    line_ids = fields.One2many('consolidation.journal.line', 'account_id', string="Account")

    linked_chart_ids = fields.Many2many('consolidation.chart', store=False, related="chart_id.children_ids")
    company_ids = fields.Many2many('res.company', store=False, related="chart_id.company_ids")
    invert_sign = fields.Boolean('Invert Balance Sign', default=False)
    sign = fields.Integer(compute='_compute_sign')

    # HIERARCHY
    #TODO I've no idea what this is for...
    using_ids = fields.Many2many('consolidation.account', 'consolidation_accounts_rel', 'used_in_ids',
                                 'using_ids', string="Consolidation Accounts")
    used_in_ids = fields.Many2many('consolidation.account', 'consolidation_accounts_rel', 'using_ids',
                                   'used_in_ids', string='Consolidated in')
    filtered_used_in_ids = fields.Many2many('consolidation.account', readonly=False,
                                            compute="_compute_filtered_used_in_ids",
                                            search="_search_filtered_used_in_ids",
                                            inverse='_inverse_filtered_used_in_ids',
                                            )

    _sql_constraints = [
        ('code_uniq', 'unique (code, chart_id)',
         "A consolidation account with the same code already exists in this consolidation."),
    ]

    def write(self, vals):
        for account in self:
            active_companies = self.env.companies
            if 'account_ids' in vals and not vals.get('account_ids'):
                vals.pop('account_ids', False)
            elif vals.get('account_ids') and vals['account_ids'][0][0] == 6 and account.company_ids - active_companies:
                next_accounts = self.env['account.account'].browse(vals['account_ids'][0][2])
                add_accounts = [(4, account.id) for account in next_accounts - account.account_ids]
                remove_accounts = [(3, account.id) for account in account.account_ids - next_accounts]
                vals['account_ids'][:1] = add_accounts + remove_accounts
        return super(ConsolidationAccount, self).write(vals)

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = self.name + ' (copy)'
        return super().copy(default)

    # COMPUTEDS

    @api.depends('group_id', 'name')
    def _compute_full_name(self):
        for record in self:
            if record.group_id:
                record.full_name = f'{record.group_id.display_name} / {record.name}'
            else:
                record.full_name = record.name

    @api.depends('used_in_ids')
    @api.depends_context('chart_id')
    def _compute_filtered_used_in_ids(self):
        """
        Compute filtered_used_in_ids field which is the list of consolidation account ids linked to this
        consolidation account filtered to only contains the ones linked to the chart contained in the context
        """
        chart_id = self.env.context.get('chart_id', False)
        for record in self:
            if chart_id:
                record.filtered_used_in_ids = record.used_in_ids.filtered(lambda x: x.chart_id.id == chart_id)
            else:
                record.filtered_used_in_ids = record.used_in_ids.ids

    def _inverse_filtered_used_in_ids(self):
        """
        Allow the write back of filtered field to the not filtered one. This method makes sure to not erase the
        consolidation accounts from other charts.
        """
        chart_id = self.env.context.get('chart_id', False)
        for record in self:
            record.used_in_ids = record.filtered_used_in_ids + record.used_in_ids.filtered(lambda x: x.chart_id.id != (chart_id or False))

    def _search_filtered_used_in_ids(self, operator, operand):
        """
        Allow the "mapped" and "not mapped" filters in the account list views.
        :rtype: list
        """
        if operator in ('!=', '=') and operand == False:
            chart_id = self.env.context.get('chart_id', False)
            domain = [('used_in_ids', '!=', False)]
            if chart_id:
                domain = expression.AND([domain, [('used_in_ids.chart_id', '=', chart_id)]])
            if operator == '=':
                domain = [('id', 'not in', self._search(domain))]
            return domain
        else:
            return [('used_in_ids', operator, operand)]

    @api.depends('group_id.sign', 'invert_sign', 'chart_id.sign')
    def _compute_sign(self):
        for record in self:
            record.sign = (-1 if record.invert_sign else 1) * (record.group_id or record.chart_id).sign

    # ORM OVERRIDES

    @api.depends('code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f'{record.code} {record.name}' if record.code else record.name

    # HELPERS

    def get_display_currency_mode(self):
        """
        Get the display name of the currency mode of this consolidation account
        :return: the repr string of the currency mode
        :rtype: str
        """
        self.ensure_one()
        return dict(self._fields['currency_mode'].selection).get(self.currency_mode)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            name_domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                name_domain = ['&', '!'] + name_domain[1:]
            domain = expression.AND([name_domain, domain])
        return self._search(domain, limit=limit, order=order)

class ConsolidationGroup(models.Model):
    _name = "consolidation.group"
    _description = "Consolidation Group"
    _order = 'parent_id asc, sequence asc, name asc'
    _parent_name = "parent_id"
    _parent_store = True

    chart_id = fields.Many2one('consolidation.chart', string="Consolidation", required=True, ondelete='cascade')
    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer()
    show_on_dashboard = fields.Boolean(default=False)
    parent_id = fields.Many2one('consolidation.group', string='Parent')
    child_ids = fields.One2many('consolidation.group', 'parent_id', 'Children')
    parent_path = fields.Char(index=True, unaccent=False)
    account_ids = fields.One2many('consolidation.account', 'group_id', 'Consolidation Account')
    line_ids = fields.One2many('consolidation.journal.line', 'group_id', 'Journal lines',
                               related="account_ids.line_ids")
    invert_sign = fields.Boolean('Invert Balance Sign', default=False)
    sign = fields.Integer(compute='_compute_sign', recursive=True)

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = self.name + ' (copy)'
        # Call manually copy to pass in the copy method of the copied records
        if self.child_ids:
            default['child_ids'] = [group.copy().id for group in self.child_ids]
        if self.account_ids:
            default['account_ids'] = [account.copy().id for account in self.account_ids]
        return super().copy(default)

    # CONSTRAINTS
    @api.constrains('child_ids', 'account_ids')
    def _check_unique_type_of_descendant(self):
        """
        Check that the section only have account children or section children but not both.
        """
        for record in self:
            if record.child_ids and len(record.child_ids) > 0 and record.account_ids and len(record.account_ids) > 0:
                raise ValidationError(_("An account group can only have accounts or other groups children but not both!"))

    @api.depends('parent_id')
    def _compute_display_name(self):
        for section in self:
            orig_section = section
            name = section.name
            while section.parent_id:
                section = section.parent_id
                name = section.name + " / " + name
            orig_section.display_name = name


    @api.depends('parent_id.sign', 'invert_sign', 'chart_id.sign')
    def _compute_sign(self):
        for group in self:
            group.sign = (-1 if group.invert_sign else 1) * (group.parent_id or group.chart_id).sign

    def _init_recursive_group_chart(self, chart_id):
        for record in self:
            record.chart_id = chart_id
            record.child_ids._init_recursive_group_chart(chart_id)
