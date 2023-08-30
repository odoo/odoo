# -*- coding: utf-8 -*-

from odoo import api, fields, models, Command, tools, _
from odoo.tools import float_compare, float_is_zero
from odoo.osv.expression import get_unaccent_wrapper
from odoo.exceptions import UserError, ValidationError
import re
from math import copysign
from collections import defaultdict
from dateutil.relativedelta import relativedelta


class AccountReconcileModelPartnerMapping(models.Model):
    _name = 'account.reconcile.model.partner.mapping'
    _description = 'Partner mapping for reconciliation models'

    model_id = fields.Many2one(comodel_name='account.reconcile.model', readonly=True, required=True, ondelete='cascade')
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner", required=True, ondelete='cascade')
    payment_ref_regex = fields.Char(string="Find Text in Label")
    narration_regex = fields.Char(string="Find Text in Notes")

    @api.constrains('narration_regex', 'payment_ref_regex')
    def validate_regex(self):
        for record in self:
            if not (record.narration_regex or record.payment_ref_regex):
                raise ValidationError(_("Please set at least one of the match texts to create a partner mapping."))
            try:
                if record.payment_ref_regex:
                    current_regex = record.payment_ref_regex
                    re.compile(record.payment_ref_regex)
                if record.narration_regex:
                    current_regex = record.narration_regex
                    re.compile(record.narration_regex)
            except re.error:
                raise ValidationError(_("The following regular expression is invalid to create a partner mapping: %s") % current_regex)


class AccountReconcileModelLine(models.Model):
    _name = 'account.reconcile.model.line'
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
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('is_off_balance', '=', False)]",
        required=True, check_company=True)
    journal_id = fields.Many2one('account.journal', string='Journal', ondelete='cascade',
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        help="This field is ignored in a bank statement reconciliation.", check_company=True)
    label = fields.Char(string='Journal Item Label')
    amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of balance'),
        ('percentage_st_line', 'Percentage of statement line'),
        ('regex', 'From label'),
    ], required=True, default='percentage')
    show_force_tax_included = fields.Boolean(compute='_compute_show_force_tax_included', help='Technical field used to show the force tax included button')
    force_tax_included = fields.Boolean(string='Tax Included in Price', help='Force the tax to be managed as a price included tax.')
    amount = fields.Float(string="Float Amount", compute='_compute_float_amount', store=True, help="Technical shortcut to parse the amount to a float")
    amount_string = fields.Char(string="Amount", default='100', required=True, help="""Value for the amount of the writeoff line
    * Percentage: Percentage of the balance, between 0 and 100.
    * Fixed: The fixed value of the writeoff. The amount will count as a debit if it is negative, as a credit if it is positive.
    * From Label: There is no need for regex delimiter, only the regex is needed. For instance if you want to extract the amount from\nR:9672938 10/07 AX 9415126318 T:5L:NA BRT: 3358,07 C:\nYou could enter\nBRT: ([\d,]+)""")
    tax_ids = fields.Many2many('account.tax', string='Taxes', ondelete='restrict', check_company=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null', check_company=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags', check_company=True,
                                        relation='account_reconcile_model_analytic_tag_rel')

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

    # Base fields.
    active = fields.Boolean(default=True)
    name = fields.Char(string='Name', required=True)
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
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
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
    match_partner = fields.Boolean(string='Partner should be set', tracking=True,
        help='The reconciliation model will only be applied when a customer/vendor is set.')
    match_partner_ids = fields.Many2many('res.partner', string='Only Those Partners',
        help='The reconciliation model will only be applied to the selected customers/vendors.')
    match_partner_category_ids = fields.Many2many('res.partner.category', string='Only Those Partner Categories',
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
    show_decimal_separator = fields.Boolean(compute='_compute_show_decimal_separator', help="Technical field to decide if we should show the decimal separator for the regex matching field.")
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
        data = self.env['account.move.line'].read_group([('reconcile_model_id', 'in', self.ids)], ['reconcile_model_id'], 'reconcile_model_id')
        mapped_data = dict([(d['reconcile_model_id'][0], d['reconcile_model_id_count']) for d in data])
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

    ####################################################
    # RECONCILIATION PROCESS
    ####################################################

    def _get_taxes_move_lines_dict(self, tax, base_line_dict, statement_line=None):
        ''' Get move.lines dict (to be passed to the create()) corresponding to a tax.
        :param tax:             An account.tax record.
        :param base_line_dict:  A dict representing the move.line containing the base amount.
        :return: A list of dict representing move.lines to be created corresponding to the tax.
        '''
        self.ensure_one()
        balance = base_line_dict['balance']

        tax_type = tax.type_tax_use
        if statement_line:
            is_refund = (tax_type == 'sale' and balance > 0) or (tax_type == 'purchase' and balance < 0)
        else:
            is_refund = (tax_type == 'sale' and balance < 0) or (tax_type == 'purchase' and balance > 0)

        res = tax.compute_all(balance, is_refund=is_refund)

        new_aml_dicts = []
        for tax_res in res['taxes']:
            tax = self.env['account.tax'].browse(tax_res['id'])
            balance = tax_res['amount']
            name = ' '.join([x for x in [base_line_dict.get('name', ''), tax_res['name']] if x])
            new_aml_dicts.append({
                'account_id': tax_res['account_id'] or base_line_dict['account_id'],
                'journal_id': base_line_dict.get('journal_id', False),
                'name': name,
                'partner_id': base_line_dict.get('partner_id'),
                'balance': balance,
                'debit': balance > 0 and balance or 0,
                'credit': balance < 0 and -balance or 0,
                'analytic_account_id': tax.analytic and base_line_dict['analytic_account_id'],
                'analytic_tag_ids': tax.analytic and base_line_dict['analytic_tag_ids'],
                'tax_repartition_line_id': tax_res['tax_repartition_line_id'],
                'tax_ids': [(6, 0, tax_res['tax_ids'])],
                'tax_tag_ids': [(6, 0, tax_res['tag_ids'])],
                'currency_id': False,
                'reconcile_model_id': self.id,
            })

            # Handle price included taxes.
            base_balance = tax_res['base']
            base_line_dict.update({
                'balance': base_balance,
                'debit': base_balance > 0 and base_balance or 0,
                'credit': base_balance < 0 and -base_balance or 0,
            })

        base_line_dict['tax_tag_ids'] = [(6, 0, res['base_tags'])]
        return new_aml_dicts

    def _get_write_off_move_lines_dict(self, st_line, residual_balance, partner_id):
        ''' Get move.lines dict (to be passed to the create()) corresponding to the reconciliation model's write-off lines.
        :param st_line:             An account.bank.statement.line record.(possibly empty, if performing manual reconciliation)
        :param residual_balance:    The residual balance of the statement line.
        :return: A list of dict representing move.lines to be created corresponding to the write-off lines.
        '''
        self.ensure_one()

        if self.rule_type == 'invoice_matching' and (not self.allow_payment_tolerance or self.payment_tolerance_param == 0):
            return []

        if st_line:
            currency = st_line.foreign_currency_id or st_line.currency_id
            matched_candidates_values = self._process_matched_candidates_data(st_line)
            st_line_residual = matched_candidates_values['balance_sign'] * matched_candidates_values['residual_balance_curr']
        else:
            currency = self.company_id.currency_id

            # No statement line
            if any(x.amount_type == 'percentage_st_line' for x in self.line_ids):
                return []

        lines_vals_list = []
        for line in self.line_ids:
            if line.amount_type == 'percentage':
                balance = currency.round(residual_balance * (line.amount / 100.0))
            elif line.amount_type == 'percentage_st_line':
                if st_line:
                    balance = currency.round(st_line_residual * (line.amount / 100.0))
                else:
                    balance = 0.0
            elif line.amount_type == 'regex':
                match = re.search(line.amount_string, st_line.payment_ref)
                if match:
                    sign = 1 if residual_balance > 0.0 else -1
                    try:
                        extracted_match_group = re.sub(r'[^\d' + self.decimal_separator + ']', '', match.group(1))
                        extracted_balance = float(extracted_match_group.replace(self.decimal_separator, '.'))
                        balance = copysign(extracted_balance * sign, residual_balance)
                    except ValueError:
                        balance = 0
                else:
                    balance = 0
            elif line.amount_type == 'fixed':
                balance = currency.round(line.amount * (1 if residual_balance > 0.0 else -1))

            if currency.is_zero(balance):
                continue

            writeoff_line = {
                'name': line.label or st_line.payment_ref,
                'balance': balance,
                'debit': balance > 0 and balance or 0,
                'credit': balance < 0 and -balance or 0,
                'account_id': line.account_id.id,
                'currency_id': currency.id,
                'analytic_account_id': line.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                'reconcile_model_id': self.id,
                'journal_id': line.journal_id.id,
                'tax_ids': [],
            }
            lines_vals_list.append(writeoff_line)

            residual_balance -= balance

            if line.tax_ids:
                taxes = line.tax_ids
                detected_fiscal_position = self.env['account.fiscal.position'].get_fiscal_position(partner_id)
                if detected_fiscal_position:
                    taxes = detected_fiscal_position.map_tax(taxes)
                writeoff_line['tax_ids'] += [Command.set(taxes.ids)]
                # Multiple taxes with force_tax_included results in wrong computation, so we
                # only allow to set the force_tax_included field if we have one tax selected
                if line.force_tax_included:
                    taxes = taxes[0].with_context(force_price_include=True)
                tax_vals_list = self._get_taxes_move_lines_dict(taxes, writeoff_line, statement_line=st_line)
                lines_vals_list += tax_vals_list
                if not line.force_tax_included:
                    for tax_line in tax_vals_list:
                        residual_balance -= tax_line['balance']

        return lines_vals_list

    ####################################################
    # RECONCILIATION CRITERIA
    ####################################################

    def _apply_rules(self, st_lines, excluded_ids=None, partner_map=None):
        ''' Apply criteria to get candidates for all reconciliation models.

        This function is called in enterprise by the reconciliation widget to match
        the statement lines with the available candidates (using the reconciliation models).

        :param st_lines:        Account.bank.statement.lines recordset.
        :param excluded_ids:    Account.move.lines to exclude.
        :param partner_map:     Dict mapping each line with new partner eventually.
        :return:                A dict mapping each statement line id with:
            * aml_ids:      A list of account.move.line ids.
            * model:        An account.reconcile.model record (optional).
            * status:       'reconciled' if the lines has been already reconciled, 'write_off' if the write-off must be
                            applied on the statement line.
        '''
        # This functions uses SQL to compute its results. We need to flush before doing anything more.
        for model_name in ('account.bank.statement', 'account.bank.statement.line', 'account.move', 'account.move.line', 'res.company', 'account.journal', 'account.account'):
            self.env[model_name].flush(self.env[model_name]._fields)

        results = {line.id: {'aml_ids': []} for line in st_lines}

        available_models = self.filtered(lambda m: m.rule_type != 'writeoff_button').sorted()
        aml_ids_to_exclude = set() # Keep track of already processed amls.
        reconciled_amls_ids = set() # Keep track of already reconciled amls.

        # First associate with each rec models all the statement lines for which it is applicable
        lines_with_partner_per_model = defaultdict(lambda: [])
        # Exclude already in the statement line associated account move lines
        excluded_ids = excluded_ids or [] + st_lines.move_id.line_ids.ids
        for st_line in st_lines:

            # Statement lines created in old versions could have a residual amount of zero. In that case, don't try to
            # match anything.
            if not st_line.amount_residual:
                continue

            mapped_partner = (partner_map and partner_map.get(st_line.id) and self.env['res.partner'].browse(partner_map[st_line.id])) or st_line.partner_id

            for rec_model in available_models:
                partner = mapped_partner or rec_model._get_partner_from_mapping(st_line)

                if rec_model._is_applicable_for(st_line, partner):
                    lines_with_partner_per_model[rec_model].append((st_line, partner))

        # Execute only one SQL query for each model (for performance)
        matched_lines = self.env['account.bank.statement.line']
        for rec_model in available_models:

            # We filter the lines for this model, in case a previous one has already found something for them
            filtered_st_lines_with_partner = [x for x in lines_with_partner_per_model[rec_model] if x[0] not in matched_lines]

            if not filtered_st_lines_with_partner:
                # No unreconciled statement line for this model
                continue

            all_model_candidates = rec_model._get_candidates(filtered_st_lines_with_partner, excluded_ids)

            for st_line, partner in filtered_st_lines_with_partner:
                candidates = all_model_candidates[st_line.id]
                if candidates:
                    model_rslt, new_reconciled_aml_ids, new_treated_aml_ids = rec_model._get_rule_result(st_line, candidates, aml_ids_to_exclude, reconciled_amls_ids, partner)

                    if model_rslt:
                        # We inject the selected partner (possibly coming from the rec model)
                        model_rslt['partner']= partner

                        results[st_line.id] = model_rslt
                        reconciled_amls_ids |= new_reconciled_aml_ids
                        aml_ids_to_exclude |= new_treated_aml_ids
                        matched_lines += st_line

        return results

    def _is_applicable_for(self, st_line, partner):
        """ Returns true iff this reconciliation model can be used to search for matches
        for the provided statement line and partner.
        """
        self.ensure_one()

        # Filter on journals, amount nature, amount and partners
        # All the conditions defined in this block are non-match conditions.
        if ((self.match_journal_ids and st_line.move_id.journal_id not in self.match_journal_ids)
            or (self.match_nature == 'amount_received' and st_line.amount < 0)
            or (self.match_nature == 'amount_paid' and st_line.amount > 0)
            or (self.match_amount == 'lower' and abs(st_line.amount) >= self.match_amount_max)
            or (self.match_amount == 'greater' and abs(st_line.amount) <= self.match_amount_min)
            or (self.match_amount == 'between' and (abs(st_line.amount) > self.match_amount_max or abs(st_line.amount) < self.match_amount_min))
            or (self.match_partner and not partner)
            or (self.match_partner and self.match_partner_ids and partner not in self.match_partner_ids)
            or (self.match_partner and self.match_partner_category_ids and not (partner.category_id & self.match_partner_category_ids))
        ):
            return False

        # Filter on label, note and transaction_type
        for record, rule_field, record_field in [(st_line, 'label', 'payment_ref'), (st_line.move_id, 'note', 'narration'), (st_line, 'transaction_type', 'transaction_type')]:
            rule_term = (self['match_' + rule_field + '_param'] or '').lower()
            record_term = (record[record_field] or '').lower()

            # This defines non-match conditions
            if ((self['match_' + rule_field] == 'contains' and rule_term not in record_term)
                or (self['match_' + rule_field] == 'not_contains' and rule_term in record_term)
                or (self['match_' + rule_field] == 'match_regex' and not re.match(rule_term, record_term))
            ):
                return False

        return True

    def _get_candidates(self, st_lines_with_partner, excluded_ids):
        """ Returns the match candidates for this rule, with respect to the provided parameters.

        :param st_lines_with_partner: A list of tuples (statement_line, partner),
                                      associating each statement line to treate with
                                      the corresponding partner, given by the partner map
        :param excluded_ids: a set containing the ids of the amls to ignore during the search
                             (because they already been matched by another rule)
        """
        self.ensure_one()

        # On big databases, it is possible that some setups will create huge queries when trying to apply reconciliation models.
        # In such cases, this query might take a very long time to run, essentially eating up all the available CPU, and proof
        # impossible to kill, because of the type of operations ran by SQL. To alleviate that, we introduce the config parameter below,
        # which essentially allows cutting the list of statement lines to match into slices, and running the matching in multiple queries.
        # This way, we avoid server overload, giving the ability to kill the process if takes too long.
        slice_size = len(st_lines_with_partner)
        slice_size_param = self.env['ir.config_parameter'].sudo().get_param('account.reconcile_model_forced_slice_size')
        if slice_size_param:
            converted_param = int(slice_size_param)
            if converted_param > 0:
                slice_size = converted_param

        treatment_slices = []
        slice_start = 0
        while slice_start < len(st_lines_with_partner):
            slice_end = slice_start + slice_size
            treatment_slices.append(st_lines_with_partner[slice_start:slice_end])
            slice_start = slice_end

        treatment_map = {
            'invoice_matching': lambda rec_model, slice: rec_model._get_invoice_matching_query(slice, excluded_ids),
            'writeoff_suggestion': lambda rec_model, slice: rec_model._get_writeoff_suggestion_query(slice, excluded_ids),
        }
        rslt = defaultdict(lambda: [])
        for treatment_slice in treatment_slices:
            query_generator = treatment_map[self.rule_type]
            query, params = query_generator(self, treatment_slice)
            self._cr.execute(query, params)

            for candidate_dict in self._cr.dictfetchall():
                rslt[candidate_dict['id']].append(candidate_dict)

        return rslt

    def _get_invoice_matching_query(self, st_lines_with_partner, excluded_ids):
        ''' Returns the query applying the current invoice_matching reconciliation
        model to the provided statement lines.

        :param st_lines_with_partner: A list of tuples (statement_line, partner),
                                      associating each statement line to treate with
                                      the corresponding partner, given by the partner map
        :param excluded_ids:    Account.move.lines to exclude.
        :return:                (query, params)
        '''
        self.ensure_one()
        if self.rule_type != 'invoice_matching':
            raise UserError(_('Programmation Error: Can\'t call _get_invoice_matching_query() for different rules than \'invoice_matching\''))

        unaccent = get_unaccent_wrapper(self._cr)

        # N.B: 'communication_flag' is there to distinguish invoice matching through the number/reference
        # (higher priority) from invoice matching using the partner (lower priority).
        query = r'''
        SELECT
            st_line.id                          AS id,
            aml.id                              AS aml_id,
            aml.currency_id                     AS aml_currency_id,
            aml.date_maturity                   AS aml_date_maturity,
            aml.amount_residual                 AS aml_amount_residual,
            aml.amount_residual_currency        AS aml_amount_residual_currency,
            ''' + self._get_select_communication_flag() + r''' AS communication_flag,
            ''' + self._get_select_payment_reference_flag() + r''' AS payment_reference_flag
        FROM account_bank_statement_line st_line
        JOIN account_move st_line_move          ON st_line_move.id = st_line.move_id
        JOIN res_company company                ON company.id = st_line_move.company_id
        , account_move_line aml
        LEFT JOIN account_move move             ON move.id = aml.move_id AND move.state = 'posted'
        LEFT JOIN account_account account       ON account.id = aml.account_id
        LEFT JOIN res_partner aml_partner       ON aml.partner_id = aml_partner.id
        LEFT JOIN account_payment payment       ON payment.move_id = move.id
        WHERE
            aml.company_id = st_line_move.company_id
            AND move.state = 'posted'
            AND account.reconcile IS TRUE
            AND aml.reconciled IS FALSE
            AND (account.internal_type NOT IN ('receivable', 'payable') OR aml.payment_id IS NULL)
        '''

        # Add conditions to handle each of the statement lines we want to match
        st_lines_queries = []
        for st_line, partner in st_lines_with_partner:
            # In case we don't have any partner for this line, we try assigning one with the rule mapping
            if st_line.amount > 0:
                st_line_subquery = r"aml.balance > 0"
            else:
                st_line_subquery = r"aml.balance < 0"

            if self.match_same_currency:
                st_line_subquery += r" AND COALESCE(aml.currency_id, company.currency_id) = %s" % (st_line.foreign_currency_id.id or st_line.move_id.currency_id.id)

            if partner:
                st_line_subquery += r" AND aml.partner_id = %s" % partner.id
            else:
                st_line_fields_consideration = [
                    (self.match_text_location_label, 'st_line.payment_ref'),
                    (self.match_text_location_note, 'st_line_move.narration'),
                    (self.match_text_location_reference, 'st_line_move.ref'),
                ]

                no_partner_query = " OR ".join([
                    r"""
                        (
                            substring(REGEXP_REPLACE(""" + sql_field + """, '[^0-9\s]', '', 'g'), '\S(?:.*\S)*') != ''
                            AND
                            (
                                (""" + self._get_select_communication_flag() + """)
                                OR
                                (""" + self._get_select_payment_reference_flag() + """)
                            )
                        )
                        OR
                        (
                            /* We also match statement lines without partners with amls
                            whose partner's name's parts (splitting on space) are all present
                            within the payment_ref, in any order, with any characters between them. */

                            aml_partner.name IS NOT NULL
                            AND """ + unaccent(sql_field) + r""" ~* ('^' || (
                                SELECT string_agg(concat('(?=.*\m', chunk[1], '\M)'), '')
                                  FROM regexp_matches(""" + unaccent("aml_partner.name") + r""", '\w{3,}', 'g') AS chunk
                            ))
                        )
                    """
                    for consider_field, sql_field in st_line_fields_consideration
                    if consider_field
                ])

                if no_partner_query:
                    st_line_subquery += " AND " + no_partner_query

            st_lines_queries.append(r"st_line.id = %s AND (%s)" % (st_line.id, st_line_subquery))

        query += r" AND (%s) " % " OR ".join(st_lines_queries)

        params = {}

        # If this reconciliation model defines a past_months_limit, we add a condition
        # to the query to only search on move lines that are younger than this limit.
        if self.past_months_limit:
            date_limit = fields.Date.context_today(self) - relativedelta(months=self.past_months_limit)
            query += " AND aml.date >= %(aml_date_limit)s"
            params['aml_date_limit'] = date_limit

        # Filter out excluded account.move.line.
        if excluded_ids:
            query += ' AND aml.id NOT IN %(excluded_aml_ids)s'
            params['excluded_aml_ids'] = tuple(excluded_ids)

        if self.matching_order == 'new_first':
            query += ' ORDER BY aml_date_maturity DESC, aml_id DESC'
        else:
            query += ' ORDER BY aml_date_maturity ASC, aml_id ASC'

        return query, params

    def _get_select_communication_flag(self):
        self.ensure_one()
        # Determine a matching or not with the statement line communication using the aml.name, move.name or move.ref.
        st_ref_list = []
        if self.match_text_location_label:
            st_ref_list += ['st_line.payment_ref']
        if self.match_text_location_note:
            st_ref_list += ['st_line_move.narration']
        if self.match_text_location_reference:
            st_ref_list += ['st_line_move.ref']

        st_ref = " || ' ' || ".join(
            "COALESCE(%s, '')" % st_ref_name
            for st_ref_name in st_ref_list
        )
        if not st_ref:
            return "FALSE"

        statement_compare = r"""(
                {move_field} IS NOT NULL AND substring(REGEXP_REPLACE({move_field}, '[^0-9\s]', '', 'g'), '\S(?:.*\S)*') != ''
                AND (
                    regexp_split_to_array(substring(REGEXP_REPLACE({move_field}, '[^0-9\s]', '', 'g'), '\S(?:.*\S)*'),'\s+')
                    && regexp_split_to_array(substring(REGEXP_REPLACE({st_ref}, '[^0-9\s]', '', 'g'), '\S(?:.*\S)*'), '\s+')
                )
            )"""
        return " OR ".join(
            statement_compare.format(move_field=field, st_ref=st_ref)
            for field in ['aml.name', 'move.name', 'move.ref']
        )

    def _get_select_payment_reference_flag(self):
        # Determine a matching or not with the statement line communication using the move.payment_reference.
        st_ref_list = []
        if self.match_text_location_label:
            st_ref_list += ['st_line.payment_ref']
        if self.match_text_location_note:
            st_ref_list += ['st_line_move.narration']
        if self.match_text_location_reference:
            st_ref_list += ['st_line_move.ref']
        if not st_ref_list:
            return "FALSE"

        # payment_reference is not used on account.move for payments; ref is used instead
        return r'''((move.payment_reference IS NOT NULL OR (payment.id IS NOT NULL AND move.ref IS NOT NULL)) AND ({}))'''.format(
            ' OR '.join(
                rf"regexp_replace(CASE WHEN payment.id IS NULL THEN move.payment_reference ELSE move.ref END, '\s+', '', 'g') = regexp_replace({st_ref}, '\s+', '', 'g')"
                for st_ref in st_ref_list
            )
        )

    def _get_partner_from_mapping(self, st_line):
        """Find partner with mapping defined on model.

        For invoice matching rules, matches the statement line against each
        regex defined in partner mapping, and returns the partner corresponding
        to the first one matching.

        :param st_line (Model<account.bank.statement.line>):
            The statement line that needs a partner to be found
        :return Model<res.partner>:
            The partner found from the mapping. Can be empty an empty recordset
            if there was nothing found from the mapping or if the function is
            not applicable.
        """
        self.ensure_one()

        if self.rule_type not in ('invoice_matching', 'writeoff_suggestion'):
            return self.env['res.partner']

        for partner_mapping in self.partner_mapping_line_ids:
            match_payment_ref = re.match(partner_mapping.payment_ref_regex, st_line.payment_ref) if partner_mapping.payment_ref_regex else True
            match_narration = re.match(partner_mapping.narration_regex, tools.html2plaintext(st_line.narration or '').rstrip()) if partner_mapping.narration_regex else True

            if match_payment_ref and match_narration:
                return partner_mapping.partner_id
        return self.env['res.partner']

    def _get_writeoff_suggestion_query(self, st_lines_with_partner, excluded_ids=None):
        ''' Returns the query applying the current writeoff_suggestion reconciliation
        model to the provided statement lines.

        :param st_lines_with_partner: A list of tuples (statement_line, partner),
                                      associating each statement line to treate with
                                      the corresponding partner, given by the partner map
        :param excluded_ids:    Account.move.lines to exclude.
        :return:                (query, params)
        '''
        self.ensure_one()

        if self.rule_type != 'writeoff_suggestion':
            raise UserError(_("Programmation Error: Can't call _get_writeoff_suggestion_query() for different rules than 'writeoff_suggestion'"))

        query = '''
            SELECT
                st_line.id                          AS id
            FROM account_bank_statement_line st_line
            WHERE st_line.id IN %(st_line_ids)s
        '''
        params = {
            'st_line_ids': tuple(st_line.id for (st_line, partner) in st_lines_with_partner),
        }

        return query, params

    def _get_rule_result(self, st_line, candidates, aml_ids_to_exclude, reconciled_amls_ids, partner_map):
        """ Get the result of a rule from the list of available candidates, depending on the
        other reconciliations performed by previous rules.
        """
        self.ensure_one()

        if self.rule_type == 'invoice_matching':
            return self._get_invoice_matching_rule_result(st_line, candidates, aml_ids_to_exclude, reconciled_amls_ids, partner_map)
        elif self.rule_type == 'writeoff_suggestion':
            return self._get_writeoff_suggestion_rule_result(st_line, partner_map), set(), set()
        else:
            return None, set(), set()

    def _get_invoice_matching_rule_result(self, st_line, candidates, aml_ids_to_exclude, reconciled_amls_ids, partner):
        new_reconciled_aml_ids = set()
        new_treated_aml_ids = set()
        candidates, priorities = self._filter_candidates(candidates, aml_ids_to_exclude, reconciled_amls_ids)

        st_line_currency = st_line.foreign_currency_id or st_line.currency_id
        candidate_currencies = set(candidate['aml_currency_id'] for candidate in candidates)
        kept_candidates = candidates
        if candidate_currencies == {st_line_currency.id}:
            kept_candidates = []
            sum_kept_candidates = 0
            for candidate in candidates:
                candidate_residual = candidate['aml_amount_residual_currency']

                if st_line_currency.compare_amounts(candidate_residual, -st_line.amount_residual) == 0:
                    # Special case: the amounts are the same, submit the line directly.
                    kept_candidates = [candidate]
                    break

                elif st_line_currency.compare_amounts(abs(sum_kept_candidates), abs(st_line.amount_residual)) < 0:
                    # Candidates' and statement line's balances have the same sign, thanks to _get_invoice_matching_query.
                    # We hence can compare their absolute value without any issue.
                    # Here, we still have room for other candidates ; so we add the current one to the list we keep.
                    # Then, we continue iterating, even if there is no room anymore, just in case one of the following candidates
                    # is an exact match, which would then be preferred on the current candidates.
                    kept_candidates.append(candidate)
                    sum_kept_candidates += candidate_residual

        # It is possible kept_candidates now contain less different priorities; update them
        kept_candidates_by_priority = self._sort_reconciliation_candidates_by_priority(kept_candidates, aml_ids_to_exclude, reconciled_amls_ids)
        priorities = set(kept_candidates_by_priority.keys())

        # We check the amount criteria of the reconciliation model, and select the
        # kept_candidates if they pass the verification.
        matched_candidates_values = self._process_matched_candidates_data(st_line, kept_candidates)
        status = self._check_rule_propositions(matched_candidates_values)
        if 'rejected' in status:
            rslt = None
        else:
            rslt = {
                'model': self,
                'aml_ids': [candidate['aml_id'] for candidate in kept_candidates],
            }
            new_treated_aml_ids = set(rslt['aml_ids'])

            # Create write-off lines (in company's currency).
            if 'allow_write_off' in status:
                residual_balance_after_rec = matched_candidates_values['residual_balance_curr'] + matched_candidates_values['candidates_balance_curr']
                writeoff_vals_list = self._get_write_off_move_lines_dict(
                    st_line,
                    matched_candidates_values['balance_sign'] * residual_balance_after_rec,
                    partner.id,
                )
                if writeoff_vals_list:
                    rslt['status'] = 'write_off'
                    rslt['write_off_vals'] = writeoff_vals_list
            else:
                writeoff_vals_list = []

            # Reconcile.
            if 'allow_auto_reconcile' in status:

                # Process auto-reconciliation. We only do that for the first two priorities, if they are not matched elsewhere.
                aml_ids = [candidate['aml_id'] for candidate in kept_candidates]
                lines_vals_list = [{'id': aml_id} for aml_id in aml_ids]

                if lines_vals_list and priorities & {1, 3} and self.auto_reconcile:

                    # Ensure this will not raise an error if case of missing account to create an open balance.
                    dummy, open_balance_vals = st_line._prepare_reconciliation(lines_vals_list + writeoff_vals_list)

                    if not open_balance_vals or open_balance_vals.get('account_id'):

                        if not st_line.partner_id and partner:
                            st_line.partner_id = partner

                        st_line.reconcile(lines_vals_list + writeoff_vals_list, allow_partial=True)

                        rslt['status'] = 'reconciled'
                        rslt['reconciled_lines'] = st_line.line_ids
                        new_reconciled_aml_ids = new_treated_aml_ids

        return rslt, new_reconciled_aml_ids, new_treated_aml_ids

    def _process_matched_candidates_data(self, statement_line, candidates=None):
        """ Simulate the reconciliation of the statement line with the candidates and
        compute some useful data to perform all the matching rules logic.

        :param statement_line:  An account.bank.statement.line record.
        :param candidates:      Fetched account.move.lines from query (dict).
        :return:                A python dict containing:
            * currency:                 The currency of the transaction.
            * statement_line:           The statement line matching the candidates.
            * candidates:               Fetched account.move.lines from query (dict).
            * reconciliation_overview:  The computed reconciliation from '_prepare_reconciliation'.
            * open_balance_vals:        The open balance returned by '_prepare_reconciliation'.
            * balance_sign:             The sign applied to the balance to make amounts always positive.
            * residual_balance:         The residual balance of the statement line before reconciling anything,
                                        always positive and expressed in company's currency.
            * candidates_balance:       The balance of candidates lines expressed in company's currency.
            * residual_balance_curr:    The residual balance of the statement line before reconciling anything,
                                        always positive and expressed in transaction's currency.
            * candidates_balance_curr:  The balance of candidates lines expressed in transaction's currency.
        """
        candidates = candidates or []

        reconciliation_overview, open_balance_vals = statement_line._prepare_reconciliation([{
            'currency_id': aml['aml_currency_id'],
            'amount_residual': aml['aml_amount_residual'],
            'amount_residual_currency': aml['aml_amount_residual_currency'],
        } for aml in candidates])

        # Compute 'residual_balance', the remaining amount to reconcile of the statement line expressed in the
        # transaction currency.
        liquidity_lines, suspense_lines, dummy = statement_line._seek_for_lines()
        if statement_line.to_check:
            stl_residual_balance = -liquidity_lines.balance
            stl_residual_balance_curr = -liquidity_lines.amount_currency
        elif suspense_lines.account_id.reconcile:
            stl_residual_balance = sum(suspense_lines.mapped('amount_residual'))
            stl_residual_balance_curr = sum(suspense_lines.mapped('amount_residual_currency'))
        else:
            stl_residual_balance = sum(suspense_lines.mapped('balance'))
            stl_residual_balance_curr = sum(suspense_lines.mapped('amount_currency'))

        # Compute 'reconciled_balance', the total reconciled amount to be reconciled by the candidates.
        candidates_balance = 0.0
        candidates_balance_curr = 0.0
        for reconciliation_vals in reconciliation_overview:
            line_vals = reconciliation_vals['line_vals']
            candidates_balance -= line_vals['debit'] - line_vals['credit']
            if line_vals['currency_id']:
                candidates_balance_curr -= line_vals['amount_currency']
            else:
                candidates_balance_curr -= line_vals['debit'] - line_vals['credit']

        # Sign amount to ease computation. Multiplying any amount from the statement line makes it positive.
        balance_sign = 1 if stl_residual_balance > 0.0 else -1

        return {
            'currency': statement_line.foreign_currency_id or statement_line.currency_id,
            'statement_line': statement_line,
            'candidates': candidates,
            'reconciliation_overview': reconciliation_overview,
            'open_balance_vals': open_balance_vals,
            'balance_sign': balance_sign,
            'residual_balance': balance_sign * stl_residual_balance,
            'candidates_balance': balance_sign * candidates_balance,
            'residual_balance_curr': balance_sign * stl_residual_balance_curr,
            'candidates_balance_curr': balance_sign * candidates_balance_curr,
        }

    def _check_rule_propositions(self, matched_candidates_values):
        """ Check restrictions that can't be handled for each move.line separately.
        Note: Only used by models having a type equals to 'invoice_matching'.

        :param matched_candidates_values: The values computed by '_process_matched_candidates_data'.
        :return: A string representing what to do with the candidates:
            * rejected:             Reject candidates.
            * allow_write_off:      Allow to generate the write-off from the reconcile model lines if specified.
            * allow_auto_reconcile: Allow to automatically reconcile entries if 'auto_validate' is enabled.
        """
        candidates = matched_candidates_values['candidates']
        currency = matched_candidates_values['currency']

        if not self.allow_payment_tolerance:
            return {'allow_write_off', 'allow_auto_reconcile'}
        if not candidates:
            return {'rejected'}

        # The statement line will be fully reconciled.
        residual_balance_after_rec = matched_candidates_values['residual_balance_curr'] + matched_candidates_values['candidates_balance_curr']
        if currency.is_zero(residual_balance_after_rec):
            return {'allow_auto_reconcile'}

        # The payment amount is higher than the sum of invoices.
        # In that case, don't check the tolerance and don't try to generate any write-off.
        if residual_balance_after_rec > 0.0:
            return {'allow_auto_reconcile'}

        # No tolerance, reject the candidates.
        if self.payment_tolerance_param == 0:
            return {'rejected'}

        # If the tolerance is expressed as a fixed amount, check the residual payment amount doesn't exceed the
        # tolerance.
        if self.payment_tolerance_type == 'fixed_amount' and -residual_balance_after_rec <= self.payment_tolerance_param:
            return {'allow_write_off', 'allow_auto_reconcile'}

        # The tolerance is expressed as a percentage between 0 and 100.0.
        reconciled_percentage_left = (residual_balance_after_rec / matched_candidates_values['candidates_balance_curr']) * 100.0
        if self.payment_tolerance_type == 'percentage' and reconciled_percentage_left <= self.payment_tolerance_param:
            return {'allow_write_off', 'allow_auto_reconcile'}

        return {'rejected'}

    def _filter_candidates(self, candidates, aml_ids_to_exclude, reconciled_amls_ids):
        """ Sorts reconciliation candidates by priority and filters them so that only
        the most prioritary are kept.
        """
        candidates_by_priority = self._sort_reconciliation_candidates_by_priority(candidates, aml_ids_to_exclude, reconciled_amls_ids)

        # This can happen if the candidates were already reconciled at this point
        if not candidates_by_priority:
            return [], set()

        max_priority = min(candidates_by_priority.keys())

        filtered_candidates = candidates_by_priority[max_priority]
        filtered_priorities = {max_priority,}

        if max_priority in (1, 3, 5):
            # We also keep the already proposed values of the same priority level
            proposed_priority = max_priority + 1
            filtered_candidates += candidates_by_priority[proposed_priority]
            if candidates_by_priority[proposed_priority]:
                filtered_priorities.add(proposed_priority)

        return filtered_candidates, filtered_priorities

    def _sort_reconciliation_candidates_by_priority(self, candidates, already_proposed_aml_ids, already_reconciled_aml_ids):
        """ Sorts the provided candidates and returns a mapping of candidates by
        priority (1 being the highest).

        The priorities are defined as follows:

        1: payment_reference_flag is true,  so the move's payment_reference
           field matches the statement line's.

        2: Same as 1, but the candidates have already been proposed for a previous statement line

        3: communication_flag is true, so either the move's ref, move's name or
           aml's name match the statement line's payment reference.

        4: Same as 3, but the candidates have already been proposed for a previous statement line

        5: candidates proposed by the query, but no match with the statement
           line's payment ref could be found.

        6: Same as 5, but the candidates have already been proposed for a previous statement line
        """
        candidates_by_priority = defaultdict(lambda: [])

        for candidate in filter(lambda x: x['aml_id'] not in already_reconciled_aml_ids, candidates):

            if candidate['payment_reference_flag']:
                priority = 1
            elif candidate['communication_flag']:
                priority = 3
            else:
                priority = 5

            if candidate['aml_id'] in already_proposed_aml_ids:
                # So, priorities 2, 4 and 6 are created here
                priority += 1

            candidates_by_priority[priority].append(candidate)

        return candidates_by_priority

    def _get_writeoff_suggestion_rule_result(self, st_line, partner):
        # Create write-off lines.
        matched_candidates_values = self._process_matched_candidates_data(st_line)
        residual_balance_after_rec = matched_candidates_values['residual_balance_curr'] + matched_candidates_values['candidates_balance_curr']
        writeoff_vals_list = self._get_write_off_move_lines_dict(
            st_line,
            matched_candidates_values['balance_sign'] * residual_balance_after_rec,
            partner.id,
        )

        rslt = {
            'model': self,
            'status': 'write_off',
            'aml_ids': [],
            'write_off_vals': writeoff_vals_list,
        }

        # Process auto-reconciliation.
        if writeoff_vals_list and self.auto_reconcile:
            if not st_line.partner_id and partner:
                st_line.partner_id = partner

            st_line.reconcile(writeoff_vals_list)
            rslt['status'] = 'reconciled'
            rslt['reconciled_lines'] = st_line.line_ids

        return rslt
