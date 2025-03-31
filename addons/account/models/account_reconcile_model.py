# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountReconcileModelLine(models.Model):
    _name = 'account.reconcile.model.line'
    _inherit = ['analytic.mixin']
    _description = 'Rules for the reconciliation model'
    _order = 'sequence, id'
    _check_company_auto = True

    model_id = fields.Many2one('account.reconcile.model', readonly=True, index='btree_not_null', ondelete='cascade')
    #related fields
    journal_id = fields.Many2one(related='model_id.journal_id')  # This field is ignored in a bank statement reconciliation.
    allow_payment_tolerance = fields.Boolean(related='model_id.allow_payment_tolerance')
    payment_tolerance_param = fields.Float(related='model_id.payment_tolerance_param')
    company_id = fields.Many2one(related='model_id.company_id', store=True)
    #model fields
    sequence = fields.Integer(required=True, default=10)
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade',
        domain="[('deprecated', '=', False), ('account_type', '!=', 'off_balance')]", check_company=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
    )
    label = fields.Char(string='Label', translate=True)
    amount_type = fields.Selection(
        selection=[
            ('fixed', 'Fixed'),
            ('percentage', 'Percentage of balance'),
            ('percentage_st_line', 'Percentage of statement line'),
            ('regex', 'From label'),
            ('from_transaction_details', 'From Transaction Details'),
        ],
        required=True,
        default='percentage',
    )
    # technical shortcut to parse the amount to a float
    amount = fields.Float(string="Float Amount", compute='_compute_float_amount', store=True)
    amount_string = fields.Char(string="Amount", default='100', required=True, help="""Value for the amount of the writeoff line
    * Percentage: Percentage of the balance, between 0 and 100.
    * Fixed: The fixed value of the writeoff. The amount will count as a debit if it is negative, as a credit if it is positive.
    * From Label: There is no need for regex delimiter, only the regex is needed. For instance if you want to extract the amount from\nR:9672938 10/07 AX 9415126318 T:5L:NA BRT: 3358,07 C:\nYou could enter\nBRT: ([\\d,]+)""")
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        ondelete='restrict',
        check_company=True,
        compute='_compute_tax_ids',
        readonly=False,
        store=True,
    )

    @api.onchange('amount_type')
    def _onchange_amount_type(self):
        self.amount_string = ''
        if self.amount_type in ('percentage', 'percentage_st_line'):
            self.amount_string = '100'
        elif self.amount_type == 'regex':
            self.amount_string = r'([\d,]+)'

    @api.depends('amount_string')
    def _compute_float_amount(self):
        for record in self:
            try:
                record.amount = float(record.amount_string)
            except ValueError:
                record.amount = 0

    @api.depends('model_id.counterpart_type', 'account_id', 'company_id', 'company_id.account_purchase_tax_id')
    def _compute_tax_ids(self):
        for line in self:
            if line.model_id.counterpart_type in ('sale', 'purchase'):
                line.tax_ids = line.tax_ids.filtered(lambda x: x.type_tax_use == line.model_id.counterpart_type)
                if not line.tax_ids:
                    line.tax_ids = line.account_id.tax_ids.filtered(lambda x: x.type_tax_use == line.model_id.counterpart_type)
                if not line.tax_ids:
                    if line.model_id.counterpart_type == 'purchase' and line.company_id.account_purchase_tax_id:
                        line.tax_ids = line.company_id.account_purchase_tax_id
                    elif line.model_id.counterpart_type == 'sale' and line.company_id.account_sale_tax_id:
                        line.tax_ids = line.company_id.account_sale_tax_id
            else:
                line.tax_ids = line.tax_ids

    @api.constrains('amount_string')
    def _validate_amount(self):
        for record in self:
            if record.amount_type == 'fixed' and record.amount == 0:
                raise UserError(_("The amount is not a number"))
            if record.amount_type == 'percentage_st_line' and record.amount == 0:
                raise UserError(_("Balance percentage can't be 0"))
            if record.amount_type == 'percentage' and record.amount == 0:
                raise UserError(_("Statement line percentage can't be 0"))
            if record.amount_type in {'regex', 'from_transaction_details'}:
                try:
                    re.compile(record.amount_string)
                except re.error:
                    raise UserError(_('The regex is not valid'))


class AccountReconcileModel(models.Model):
    _name = 'account.reconcile.model'
    _description = 'Preset to create journal entries during a invoices and payments matching'
    _inherit = ['mail.thread']
    _order = 'sequence, id'
    _check_company_auto = True

    _name_unique = models.Constraint(
        'unique(name, company_id)',
        'A reconciliation model already bears this name.',
    )

    # Base fields.
    active = fields.Boolean(default=True)
    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(required=True, default=10)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)

    #RN# 
    #deleted rule_type, matching_order, match_note, match_note_param, match_transaction_details, match_transaction_details_param, match_text_location_label, match_text_location_note, match_text_location_reference, match_same_currency, match_partner_category_ids, match_partner, past_months_limit, decimal_separator, show_decimal_separator, partner_mapping_line_ids (+class)
    #auto_reconcile boolean --> trigger selection
    trigger = fields.Selection([('manual', 'Manual'), ('auto_reconcile', 'Automated')], default='manual', required=True, tracking=True,
        help='Validate the statement line automatically (reconciliation based on your rule).')
    to_check = fields.Boolean(string='To Check', default=False, help='This matching rule is used when the user is not certain of all the information of the counterpart.')
    counterpart_type = fields.Selection(
        selection=[
            ('general', 'Journal Entry'),
            ('sale', 'Customer Invoices'),
            ('purchase', 'Vendor Bills'),
        ],
        string="Counterpart Type",
        default='general',
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Journal",
        help="The journal in which the counterpart entry will be created.",
        check_company=True,
        store=True,
        readonly=False,
        compute='_compute_journal_id',
    )

    # ===== Conditions =====
    match_journal_ids = fields.Many2many('account.journal', string='Journals Availability',
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]",
        check_company=True,
        help='The reconciliation model will only be available from the selected journals.')
    match_amount = fields.Selection(selection=[
        ('lower', 'Is Lower Than'),
        ('greater', 'Is Greater Than'),
        ('between', 'Is Between'),
    ], string='Amount', tracking=True,
        help='The reconciliation model will only be applied when the amount being lower than, greater than or between specified amount(s).')
    match_amount_min = fields.Float(string='Amount Min Parameter', tracking=True)
    match_amount_max = fields.Float(string='Amount Max Parameter', tracking=True)
    match_label = fields.Selection(selection=[
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('match_regex', 'Match Regex'),
    ], string='Label', tracking=True, help='''The reconciliation model will only be applied when the label:
        * Contains: The proposition label must contains this string (case insensitive).
        * Not Contains: Negation of "Contains".
        * Match Regex: Define your own regular expression.''')
    match_label_param = fields.Char(string='Label Parameter', tracking=True)
    allow_payment_tolerance = fields.Boolean(
        string="Payment Tolerance",
        default=True,
        tracking=True,
        help="Difference accepted in case of underpayment.",
    )
    payment_tolerance_param = fields.Float(
        string="Gap",
        compute='_compute_payment_tolerance_param',
        readonly=False,
        store=True,
        tracking=True,
        help="The sum of total residual amount propositions matches the statement line amount under this amount/percentage.",
    )
    payment_tolerance_type = fields.Selection(
        selection=[('percentage', "in percentage"), ('fixed_amount', "in amount")],
        default='percentage',
        required=True,
        tracking=True,
        help="The sum of total residual amount propositions and the statement line amount allowed gap type.",
    )
    match_partner_ids = fields.Many2many('res.partner', string='Partners',
        help='The reconciliation model will only be applied to the selected customers/vendors.')

    line_ids = fields.One2many('account.reconcile.model.line', 'model_id', copy=True)
    number_entries = fields.Integer(string='Number of entries related to this model', compute='_compute_number_entries')

    def action_set_manual(self):
        for model in self:
            model.trigger = 'manual'

    def action_set_auto_reconcile(self):
        for model in self:
            model.trigger = 'auto_reconcile'

    def action_reconcile_stat(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        self._cr.execute('''
            SELECT ARRAY_AGG(DISTINCT move_id)
            FROM account_move_line
            WHERE reconcile_model_id = %s
        ''', [self.id])
        action.update({
            'context': {},
            'domain': [('id', 'in', self._cr.fetchone()[0])],
            'help': """<p class="o_view_nocontent_empty_folder">{}</p>""".format(_('This reconciliation model has created no entry so far')),
        })
        return action

    def _compute_number_entries(self):
        data = self.env['account.move.line']._read_group([('reconcile_model_id', 'in', self.ids)], ['reconcile_model_id'], ['__count'])
        mapped_data = {reconcile_model.id: count for reconcile_model, count in data}
        for model in self:
            model.number_entries = mapped_data.get(model.id, 0)

    @api.depends('payment_tolerance_param', 'payment_tolerance_type')
    def _compute_payment_tolerance_param(self):
        for record in self:
            if record.payment_tolerance_type == 'percentage':
                record.payment_tolerance_param = min(100.0, max(0.0, record.payment_tolerance_param))
            else:
                record.payment_tolerance_param = max(0.0, record.payment_tolerance_param)

    @api.depends('counterpart_type')
    def _compute_journal_id(self):
        for record in self:
            if record.journal_id.type != record.counterpart_type:
                record.journal_id = None
            else:
                record.journal_id = record.journal_id

    @api.constrains('allow_payment_tolerance', 'payment_tolerance_param', 'payment_tolerance_type')
    def _check_payment_tolerance_param(self):
        for record in self:
            if record.allow_payment_tolerance:
                if record.payment_tolerance_type == 'percentage' and not 0 <= record.payment_tolerance_param <= 100:
                    raise ValidationError(_("A payment tolerance defined as a percentage should always be between 0 and 100"))
                elif record.payment_tolerance_type == 'fixed_amount' and record.payment_tolerance_param < 0:
                    raise ValidationError(_("A payment tolerance defined as an amount should always be higher than 0"))

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default)
        if default.get('name'):
            return vals_list
        for model, vals in zip(self, vals_list):
            name = _("%s (copy)", model.name)
            while self.env['account.reconcile.model'].search_count([('name', '=', name)], limit=1):
                name = _("%s (copy)", name)
            vals['name'] = name
        return vals_list
