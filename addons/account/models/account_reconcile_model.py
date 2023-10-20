# -*- coding: utf-8 -*-

from odoo import api, fields, models, Command, tools, _
from odoo.exceptions import UserError, ValidationError
import re
from math import copysign
from collections import defaultdict
from dateutil.relativedelta import relativedelta


class AccountReconcileModelPartnerMapping(models.Model):
    _name = 'account.reconcile.model.partner.mapping'
    _description = 'Partner mapping for reconciliation models'
    _check_company_auto = True

    model_id = fields.Many2one(comodel_name='account.reconcile.model', readonly=True, required=True, ondelete='cascade')
    company_id = fields.Many2one(related='model_id.company_id')
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner", required=True, ondelete='cascade', check_company=True)
    payment_ref_regex = fields.Char(string="Find Text in Label")
    narration_regex = fields.Char(string="Find Text in Notes")

    @api.constrains('narration_regex', 'payment_ref_regex')
    def validate_regex(self):
        for record in self:
            if not (record.narration_regex or record.payment_ref_regex):
                raise ValidationError(_("Please set at least one of the match texts to create a partner mapping."))
            current_regex = None
            try:
                if record.payment_ref_regex:
                    current_regex = record.payment_ref_regex
                    re.compile(record.payment_ref_regex)
                if record.narration_regex:
                    current_regex = record.narration_regex
                    re.compile(record.narration_regex)
            except re.error:
                raise ValidationError(_("The following regular expression is invalid to create a partner mapping: %s", current_regex))


class AccountReconcileModelLine(models.Model):
    _name = 'account.reconcile.model.line'
    _inherit = 'analytic.mixin'
    _description = 'Rules for the reconciliation model'
    _order = 'sequence, id'
    _check_company_auto = True

    model_id = fields.Many2one('account.reconcile.model', readonly=True, ondelete='cascade')
    allow_payment_tolerance = fields.Boolean(related='model_id.allow_payment_tolerance')
    payment_tolerance_param = fields.Float(related='model_id.payment_tolerance_param')
    rule_type = fields.Selection(related='model_id.rule_type')
    company_id = fields.Many2one(related='model_id.company_id', store=True)
    sequence = fields.Integer(required=True, default=10)
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade',
        domain="[('deprecated', '=', False), ('account_type', '!=', 'off_balance')]",
        required=True, check_company=True)

    # This field is ignored in a bank statement reconciliation.
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade',
        domain="[('type', '=', 'general')]", check_company=True)
    label = fields.Char(string='Journal Item Label', translate=True)
    amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of balance'),
        ('percentage_st_line', 'Percentage of statement line'),
        ('regex', 'From label'),
    ], required=True, default='percentage')

    # used to show the force tax included button'
    show_force_tax_included = fields.Boolean(compute='_compute_show_force_tax_included')
    force_tax_included = fields.Boolean(string='Tax Included in Price', help='Force the tax to be managed as a price included tax.')
    # technical shortcut to parse the amount to a float
    amount = fields.Float(string="Float Amount", compute='_compute_float_amount', store=True)
    amount_string = fields.Char(string="Amount", default='100', required=True, help="""Value for the amount of the writeoff line
    * Percentage: Percentage of the balance, between 0 and 100.
    * Fixed: The fixed value of the writeoff. The amount will count as a debit if it is negative, as a credit if it is positive.
    * From Label: There is no need for regex delimiter, only the regex is needed. For instance if you want to extract the amount from\nR:9672938 10/07 AX 9415126318 T:5L:NA BRT: 3358,07 C:\nYou could enter\nBRT: ([\d,]+)""")
    tax_ids = fields.Many2many('account.tax', string='Taxes', ondelete='restrict', check_company=True)

    @api.onchange('tax_ids')
    def _onchange_tax_ids(self):
        # Multiple taxes with force_tax_included results in wrong computation, so we
        # only allow to set the force_tax_included field if we have one tax selected
        if len(self.tax_ids) != 1:
            self.force_tax_included = False

    @api.depends('tax_ids')
    def _compute_show_force_tax_included(self):
        for record in self:
            record.show_force_tax_included = False if len(record.tax_ids) != 1 else True

    @api.onchange('amount_type')
    def _onchange_amount_type(self):
        self.amount_string = ''
        if self.amount_type in ('percentage', 'percentage_st_line'):
            self.amount_string = '100'
        elif self.amount_type == 'regex':
            self.amount_string = '([\d,]+)'

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

    _sql_constraints = [('name_unique', 'unique(name, company_id)', 'A reconciliation model already bears this name.')]

    # Base fields.
    active = fields.Boolean(default=True)
    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(required=True, default=10)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    rule_type = fields.Selection(selection=[
        ('writeoff_button', 'Button to generate counterpart entry'),
        ('writeoff_suggestion', 'Rule to suggest counterpart entry'),
        ('invoice_matching', 'Rule to match invoices/bills'),
    ], string='Type', default='writeoff_button', required=True, tracking=True)
    auto_reconcile = fields.Boolean(string='Auto-validate', tracking=True,
        help='Validate the statement line automatically (reconciliation based on your rule).')
    to_check = fields.Boolean(string='To Check', default=False, help='This matching rule is used when the user is not certain of all the information of the counterpart.')
    matching_order = fields.Selection(
        selection=[
            ('old_first', 'Oldest first'),
            ('new_first', 'Newest first'),
        ],
        required=True,
        default='old_first',
        tracking=True,
    )

    # ===== Conditions =====
    match_text_location_label = fields.Boolean(
        default=True,
        help="Search in the Statement's Label to find the Invoice/Payment's reference",
        tracking=True,
    )
    match_text_location_note = fields.Boolean(
        default=False,
        help="Search in the Statement's Note to find the Invoice/Payment's reference",
        tracking=True,
    )
    match_text_location_reference = fields.Boolean(
        default=False,
        help="Search in the Statement's Reference to find the Invoice/Payment's reference",
        tracking=True,
    )
    match_journal_ids = fields.Many2many('account.journal', string='Journals Availability',
        domain="[('type', 'in', ('bank', 'cash'))]",
        check_company=True,
        help='The reconciliation model will only be available from the selected journals.')
    match_nature = fields.Selection(selection=[
        ('amount_received', 'Received'),
        ('amount_paid', 'Paid'),
        ('both', 'Paid/Received')
    ], string='Amount Type', required=True, default='both', tracking=True,
        help='''The reconciliation model will only be applied to the selected transaction type:
        * Amount Received: Only applied when receiving an amount.
        * Amount Paid: Only applied when paying an amount.
        * Amount Paid/Received: Applied in both cases.''')
    match_amount = fields.Selection(selection=[
        ('lower', 'Is Lower Than'),
        ('greater', 'Is Greater Than'),
        ('between', 'Is Between'),
    ], string='Amount Condition', tracking=True,
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
    match_note = fields.Selection(selection=[
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('match_regex', 'Match Regex'),
    ], string='Note', tracking=True, help='''The reconciliation model will only be applied when the note:
        * Contains: The proposition note must contains this string (case insensitive).
        * Not Contains: Negation of "Contains".
        * Match Regex: Define your own regular expression.''')
    match_note_param = fields.Char(string='Note Parameter', tracking=True)
    match_transaction_type = fields.Selection(selection=[
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('match_regex', 'Match Regex'),
    ], string='Transaction Type', tracking=True, help='''The reconciliation model will only be applied when the transaction type:
        * Contains: The proposition transaction type must contains this string (case insensitive).
        * Not Contains: Negation of "Contains".
        * Match Regex: Define your own regular expression.''')
    match_transaction_type_param = fields.Char(string='Transaction Type Parameter', tracking=True)
    match_same_currency = fields.Boolean(string='Same Currency', default=True, tracking=True,
        help='Restrict to propositions having the same currency as the statement line.')
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
    match_partner = fields.Boolean(string='Partner is Set', tracking=True,
        help='The reconciliation model will only be applied when a customer/vendor is set.')
    match_partner_ids = fields.Many2many('res.partner', string='Matching partners',
        help='The reconciliation model will only be applied to the selected customers/vendors.')
    match_partner_category_ids = fields.Many2many('res.partner.category', string='Matching categories',
        help='The reconciliation model will only be applied to the selected customer/vendor categories.')

    line_ids = fields.One2many('account.reconcile.model.line', 'model_id', copy=True)
    partner_mapping_line_ids = fields.One2many(string="Partner Mapping Lines",
                                               comodel_name='account.reconcile.model.partner.mapping',
                                               inverse_name='model_id',
                                               help="The mapping uses regular expressions.\n"
                                                    "- To Match the text at the beginning of the line (in label or notes), simply fill in your text.\n"
                                                    "- To Match the text anywhere (in label or notes), put your text between .*\n"
                                                    "  e.g: .*N°48748 abc123.*")
    past_months_limit = fields.Integer(
        string="Search Months Limit",
        default=18,
        tracking=True,
        help="Number of months in the past to consider entries from when applying this model.",
    )
    decimal_separator = fields.Char(
        default=lambda self: self.env['res.lang']._lang_get(self.env.user.lang).decimal_point,
        tracking=True,
        help="Every character that is nor a digit nor this separator will be removed from the matching string",
    )
    # used to decide if we should show the decimal separator for the regex matching field
    show_decimal_separator = fields.Boolean(compute='_compute_show_decimal_separator')
    number_entries = fields.Integer(string='Number of entries related to this model', compute='_compute_number_entries')

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

    @api.depends('line_ids.amount_type')
    def _compute_show_decimal_separator(self):
        for record in self:
            record.show_decimal_separator = any(l.amount_type == 'regex' for l in record.line_ids)

    @api.depends('payment_tolerance_param', 'payment_tolerance_type')
    def _compute_payment_tolerance_param(self):
        for record in self:
            if record.payment_tolerance_type == 'percentage':
                record.payment_tolerance_param = min(100.0, max(0.0, record.payment_tolerance_param))
            else:
                record.payment_tolerance_param = max(0.0, record.payment_tolerance_param)

    @api.constrains('allow_payment_tolerance', 'payment_tolerance_param', 'payment_tolerance_type')
    def _check_payment_tolerance_param(self):
        for record in self:
            if record.allow_payment_tolerance:
                if record.payment_tolerance_type == 'percentage' and not 0 <= record.payment_tolerance_param <= 100:
                    raise ValidationError(_("A payment tolerance defined as a percentage should always be between 0 and 100"))
                elif record.payment_tolerance_type == 'fixed_amount' and record.payment_tolerance_param < 0:
                    raise ValidationError(_("A payment tolerance defined as an amount should always be higher than 0"))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if default.get('name'):
            return super(AccountReconcileModel, self).copy(default)
        name = _("%s (copy)", self.name)
        while self.env['account.reconcile.model'].search([('name', '=', name)], limit=1):
            name = _("%s (copy)", name)
        default['name'] = name
        return super(AccountReconcileModel, self).copy(default)
