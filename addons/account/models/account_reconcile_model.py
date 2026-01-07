# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountReconcileModelLine(models.Model):
    _name = 'account.reconcile.model.line'
    _inherit = ['analytic.mixin']
    _description = 'Rules for the reconciliation model'
    _order = 'sequence, id'
    _check_company_auto = True

    model_id = fields.Many2one('account.reconcile.model', readonly=True, index='btree_not_null', ondelete='cascade')
    company_id = fields.Many2one(related='model_id.company_id', store=True)
    sequence = fields.Integer(required=True, default=10)
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade',
        domain="[('account_type', '!=', 'off_balance')]", check_company=True)
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
        ],
        required=True,
        default='percentage',
    )
    # technical shortcut to parse the amount to a float
    amount = fields.Float(string="Float Amount", compute='_compute_float_amount', store=True)
    amount_string = fields.Char(
        string="Amount",
        default='100',
        required=True,
        help="""Value for the amount of the writeoff line
    * Percentage: Percentage of the balance, between 0 and 100.
    * Fixed: The fixed value of the writeoff. The amount will count as a debit if it is negative, as a credit if it is positive.
    * From Label: There is no need for regex delimiter, only the regex is needed. For instance if you want to extract the amount from\nR:9672938 10/07 AX 9415126318 T:5L:NA BRT: 3358,07 C:\nYou could enter\nBRT: ([\\d,]+)
    If the label is "01870912 0009065 00115" and you need the amount in decimal
    format (e.g. 90.65), you can use a regex with capturing groups, for example:
        \\s+0*(\\d+?)(\\d{2})(?=\\s)
    In this case:
    • the first group captures the integer part
    • the second group captures the decimal part (last two digits)
    """)
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        ondelete='restrict',
        check_company=True,
    )

    @api.onchange('amount_type')
    def _onchange_amount_type(self):
        self.amount_string = ''
        if self.amount_type in ('percentage', 'percentage_st_line'):
            self.amount_string = '100'
        elif self.amount_type in ('regex', 'from_transaction_details'):
            self.amount_string = r'([\d,]+)'

    @api.depends('amount_string')
    def _compute_float_amount(self):
        for record in self:
            try:
                record.amount = float(record.amount_string)
            except ValueError:
                record.amount = 0

    @api.constrains('amount_string')
    def _validate_amount(self):
        for record in self:
            if record.amount_type == 'fixed' and record.amount == 0:
                raise UserError(_("The amount is not a number"))
            if record.amount_type == 'percentage_st_line' and record.amount == 0:
                raise UserError(_("Balance percentage can't be 0"))
            if record.amount_type == 'percentage' and record.amount == 0:
                raise UserError(_("Statement line percentage can't be 0"))
            if record.amount_type == 'regex':
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

    # Base fields.
    active = fields.Boolean(default=True)
    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(required=True, default=10)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)

    trigger = fields.Selection([('manual', 'Manual'), ('auto_reconcile', 'Automated')], default='manual', required=True, tracking=True,
        help='Validate the statement line automatically (reconciliation based on your rule).')
    next_activity_type_id = fields.Many2one(
        comodel_name='mail.activity.type',
        string='Next Activity')

    # ===== Conditions =====
    can_be_proposed = fields.Boolean(
        compute='_compute_can_be_proposed', store=True,
        copy=False,
    )
    mapped_partner_id = fields.Many2one(
        comodel_name='res.partner',
        compute='_compute_partner_mapping', store=True,
        copy=False,
    )
    match_journal_ids = fields.Many2many('account.journal', string='Journals',
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]",
        check_company=True,
        help='The reconciliation model will only be available from the selected journals.')
    match_amount = fields.Selection(selection=[
        ('lower', 'Is lower than or equal to'),
        ('greater', 'Is greater than or equal to'),
        ('between', 'Is between'),
    ], string='Amount', tracking=True,
        help='The reconciliation model will only be applied when the amount being lower than, greater than or between specified amount(s).')
    match_amount_min = fields.Float(string='Amount Min Parameter', tracking=True)
    match_amount_max = fields.Float(string='Amount Max Parameter', tracking=True)
    match_label = fields.Selection(selection=[
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('match_regex', 'Match Regex'),
    ], string='Label', tracking=True, help='''The reconciliation model will only be applied when either the statement line label, the transaction details or the note matches the following:
        * Contains: The statement line must contains this string (case insensitive).
        * Not Contains: Negation of "Contains".
        * Match Regex: Define your own regular expression.''')
    match_label_param = fields.Char(string='Label Parameter', tracking=True)
    match_partner_ids = fields.Many2many('res.partner', string='Partners',
        help='The reconciliation model will only be applied to the selected customers/vendors.')

    line_ids = fields.One2many('account.reconcile.model.line', 'model_id', copy=True)

    @api.constrains('match_label', 'match_label_param')
    def _check_match_label_param(self):
        for record in self:
            if record.match_label == 'match_regex':
                try:
                    re.compile(record.match_label_param)
                except re.error:
                    raise UserError(_('The regex is not valid'))

    @api.depends('mapped_partner_id', 'match_label', 'match_amount', 'match_partner_ids', 'trigger')
    def _compute_can_be_proposed(self):
        for model in self:
            model.can_be_proposed = not model.mapped_partner_id and (model.match_label or model.match_amount or model.match_partner_ids or model.trigger == 'auto_reconcile')

    @api.depends('match_label', 'line_ids.partner_id', 'line_ids.account_id')
    def _compute_partner_mapping(self):
        for model in self:
            is_partner_mapping = model.match_label and len(model.line_ids) == 1 and model.line_ids[0].partner_id and not model.line_ids[0].account_id
            model.mapped_partner_id = is_partner_mapping and model.line_ids[0].partner_id.id

    def action_set_manual(self):
        self.trigger = 'manual'

    def action_set_auto_reconcile(self):
        self.trigger = 'auto_reconcile'

    def action_reconcile_stat(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        self.env.cr.execute('''
            SELECT ARRAY_AGG(DISTINCT move_id)
            FROM account_move_line
            WHERE reconcile_model_id = %s
        ''', [self.id])
        action.update({
            'context': {},
            'domain': [('id', 'in', self.env.cr.fetchone()[0])],
            'help': """<p class="o_view_nocontent_empty_folder">{}</p>""".format(_('This reconciliation model has created no entry so far')),
        })
        return action

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
