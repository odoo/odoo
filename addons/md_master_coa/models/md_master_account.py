from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

CATEGORY_COLOR = {
    'Asset': 4,           # blue
    'Liability': 1,       # red
    'Equity': 10,         # teal
    'Revenue': 6,         # green
    'Cost of Goods Sold': 2,  # orange
    'Expense': 3,         # yellow
    'Other': 0,           # grey
}

ODOO_ACCOUNT_TYPES = [
    ('asset_receivable', 'Receivable'),
    ('asset_cash', 'Bank and Cash'),
    ('asset_current', 'Current Assets'),
    ('asset_non_current', 'Non-current Assets'),
    ('asset_prepayments', 'Prepayments'),
    ('asset_fixed', 'Fixed Assets'),
    ('liability_payable', 'Payable'),
    ('liability_current', 'Current Liabilities'),
    ('liability_non_current', 'Non-current Liabilities'),
    ('equity', 'Equity'),
    ('equity_unaffected', 'Current Year Earnings'),
    ('income', 'Income'),
    ('income_other', 'Other Income'),
    ('expense', 'Expenses'),
    ('expense_depreciation', 'Depreciation'),
    ('expense_direct_cost', 'Cost of Revenue'),
    ('off_balance', 'Off-Balance Sheet'),
]


class MdMasterAccount(models.Model):
    """Master Chart of Accounts — single source of truth for MD Portfolio.

    Header accounts (type='Header') are organisational; transactions must
    never be posted to them.  Detail accounts are the operative leaves.
    Each company account can be linked back to a master account via the
    md.account.mapping model or directly via account.account.master_account_id.
    """
    _name = 'md.master.account'
    _description = 'MD Master Chart of Accounts'
    _order = 'code'
    _parent_field = 'parent_id'
    _parent_store = True
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Core fields (mirror CSV columns) ────────────────────────────────────
    code = fields.Char(
        'Account Code', required=True, index=True, tracking=True,
        help='Numeric code aligned with MD standard numbering (10000–80000 range).')
    description = fields.Char(
        'Account Name', required=True, tracking=True)
    long_description = fields.Text(
        'Full Description',
        help='Detailed description used in onboarding and documentation.')
    account_type = fields.Selection(
        [('Header', 'Header'), ('Detail', 'Detail')],
        string='Account Type', required=True, default='Detail', tracking=True,
        help='Header accounts are grouping nodes; never post transactions to them.')
    category = fields.Selection(
        [
            ('Asset', 'Asset'),
            ('Liability', 'Liability'),
            ('Equity', 'Equity'),
            ('Revenue', 'Revenue'),
            ('Cost of Goods Sold', 'Cost of Goods Sold'),
            ('Expense', 'Expense'),
            ('Other', 'Other'),
        ],
        string='Category', required=True, tracking=True)
    fs_mapping = fields.Selection(
        [('Balance Sheet', 'Balance Sheet'), ('Income Statement', 'Income Statement')],
        string='Financial Statement', tracking=True,
        help='Which financial statement this account belongs to.')
    normal_balance = fields.Selection(
        [('Debit', 'Debit'), ('Credit', 'Credit')],
        string='Normal Balance', tracking=True)

    # ── Hierarchy ─────────────────────────────────────────────────────────
    parent_id = fields.Many2one(
        'md.master.account', 'Parent Account',
        index=True, ondelete='restrict')
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        'md.master.account', 'parent_id', 'Sub-accounts')
    child_count = fields.Integer(compute='_compute_child_count', store=True)

    # ── Classification ───────────────────────────────────────────────────
    subcategory = fields.Char('Subcategory', tracking=True)
    cash_flow_classification = fields.Selection(
        [
            ('Operating Activities', 'Operating Activities'),
            ('Investing Activities', 'Investing Activities'),
            ('Financing Activities', 'Financing Activities'),
        ],
        string='Cash Flow Classification')
    cost_center = fields.Char('Cost Center')
    gaap_classification = fields.Char('GAAP Classification')
    odoo_account_type = fields.Selection(
        ODOO_ACCOUNT_TYPES,
        string='Odoo Account Type',
        help='Maps to account.account.account_type for automated company-account creation.')

    # ── Compliance & metadata ────────────────────────────────────────────
    regulatory_mapping = fields.Text(
        'Regulatory Mapping',
        help='IFRS / ASC references (e.g. IAS 1, ASC 210).')
    tags = fields.Char(
        'Tags',
        help='Comma-separated tags for search and reporting (e.g. "asset, current, cash").')
    default_vendors = fields.Char(
        'Default Vendors',
        help='Typical vendors associated with this account.')
    start_date = fields.Date('Effective From')
    end_date = fields.Date('Effective To')
    notes = fields.Text('Notes')
    detailed_description = fields.Text('Detailed Description')

    # ── Phase-2 QBO fields ───────────────────────────────────────────────
    qbo_account_id = fields.Char(
        'QBO Account ID', copy=False,
        help='QuickBooks Online internal account ID. Populated after first sync.')
    qbo_account_type = fields.Char(
        'QBO Account Type', copy=False,
        help='Account type string as recognised by the QBO API.')
    qbo_sync_state = fields.Selection(
        [
            ('not_synced', 'Not Synced'),
            ('synced', 'Synced'),
            ('pending_push', 'Pending Push'),
            ('pending_pull', 'Pending Pull'),
            ('error', 'Sync Error'),
        ],
        string='QBO Sync Status', default='not_synced', tracking=True)
    qbo_last_sync = fields.Datetime('Last QBO Sync', copy=False)

    # ── UI helpers ───────────────────────────────────────────────────────
    active = fields.Boolean(default=True)
    color = fields.Integer(
        'Color Index', compute='_compute_color', store=True,
        help='Kanban colour band derived from account category.')
    display_name = fields.Char(
        compute='_compute_display_name', store=True, recursive=True)

    # ── QBO mapping back-reference ───────────────────────────────────────
    mapping_ids = fields.One2many(
        'md.account.mapping', 'master_account_id', 'Company Mappings')

    # ── Cross-company counters ───────────────────────────────────────────
    company_account_count = fields.Integer(
        'Linked Company Accounts',
        compute='_compute_company_account_count',
        help='How many company-level accounts across all branches are linked to this master account.')
    mapping_count = fields.Integer(
        'QBO Mappings', compute='_compute_mapping_count')
    move_line_count = fields.Integer(
        'Journal Items', compute='_compute_move_line_count',
        help='Total journal items posted to any linked company account.')

    # ── SQL constraints ──────────────────────────────────────────────────
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Account code must be unique in the master chart.'),
    ]

    # ── Compute methods ──────────────────────────────────────────────────

    @api.depends('code', 'description')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.code} {rec.description}' if rec.code else rec.description

    @api.depends('category')
    def _compute_color(self):
        for rec in self:
            rec.color = CATEGORY_COLOR.get(rec.category, 0)

    @api.depends('child_ids')
    def _compute_child_count(self):
        for rec in self:
            rec.child_count = len(rec.child_ids)

    def _compute_company_account_count(self):
        AccountAccount = self.env['account.account']
        for rec in self:
            rec.company_account_count = AccountAccount.sudo().search_count(
                [('master_account_id', '=', rec.id)])

    def _compute_mapping_count(self):
        Mapping = self.env['md.account.mapping']
        for rec in self:
            rec.mapping_count = Mapping.search_count(
                [('master_account_id', '=', rec.id)])

    def _compute_move_line_count(self):
        MoveLine = self.env['account.move.line']
        for rec in self:
            linked_accounts = self.env['account.account'].sudo().search(
                [('master_account_id', '=', rec.id)])
            if linked_accounts:
                rec.move_line_count = MoveLine.sudo().search_count(
                    [('account_id', 'in', linked_accounts.ids)])
            else:
                rec.move_line_count = 0

    # ── Validation ───────────────────────────────────────────────────────

    @api.constrains('parent_id')
    def _check_parent(self):
        if not self._check_recursion():
            raise ValidationError(_('A master account cannot be its own ancestor.'))

    @api.constrains('account_type', 'parent_id')
    def _check_header_no_parent(self):
        for rec in self:
            if rec.account_type == 'Header' and rec.parent_id:
                raise ValidationError(
                    _('Header account "%s" cannot have a parent. '
                      'Headers are top-level organisers.') % rec.display_name)

    # ── Action buttons ───────────────────────────────────────────────────

    def action_view_company_accounts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Company Accounts — %s') % self.display_name,
            'res_model': 'account.account',
            'view_mode': 'list,form',
            'domain': [('master_account_id', '=', self.id)],
            'context': {'default_master_account_id': self.id},
        }

    def action_view_move_lines(self):
        self.ensure_one()
        linked = self.env['account.account'].sudo().search(
            [('master_account_id', '=', self.id)])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items — %s') % self.display_name,
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('account_id', 'in', linked.ids)],
        }

    def action_view_child_accounts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sub-accounts of %s') % self.display_name,
            'res_model': 'md.master.account',
            'view_mode': 'list,kanban,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id},
        }

    def action_view_mappings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('QBO Mappings — %s') % self.display_name,
            'res_model': 'md.account.mapping',
            'view_mode': 'list,form',
            'domain': [('master_account_id', '=', self.id)],
            'context': {'default_master_account_id': self.id},
        }

    def action_push_to_qbo(self):
        """Phase 2: push this account to QuickBooks Online."""
        self.ensure_one()
        # Scaffold — real implementation lives in qbo_bridge module.
        self.qbo_sync_state = 'pending_push'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('QBO Sync queued'),
                'message': _('Account "%s" has been queued for push to QuickBooks Online.') % self.display_name,
                'type': 'info',
                'sticky': False,
            },
        }

    # ── Name search ──────────────────────────────────────────────────────

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('code', operator, name), ('description', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)
