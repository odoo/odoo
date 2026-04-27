# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models, Command
from odoo.osv import expression
from odoo.tools.misc import formatLang, frozendict

import markupsafe
import uuid


class BankRecWidgetLine(models.Model):
    _name = "bank.rec.widget.line"
    _inherit = "analytic.mixin"
    _description = "Line of the bank reconciliation widget"

    # This model is never saved inside the database.
    # _auto=False' & _table_query = "0" prevent the ORM to create the corresponding postgresql table.
    _auto = False
    _table_query = "0"

    wizard_id = fields.Many2one(comodel_name='bank.rec.widget')
    index = fields.Char(compute='_compute_index')
    flag = fields.Selection(
        selection=[
            ('liquidity', 'liquidity'),
            ('new_aml', 'new_aml'),
            ('aml', 'aml'),
            ('exchange_diff', 'exchange_diff'),
            ('tax_line', 'tax_line'),
            ('manual', 'manual'),
            ('early_payment', 'early_payment'),
            ('auto_balance', 'auto_balance'),
        ],
    )

    journal_default_account_id = fields.Many2one(
        related='wizard_id.st_line_id.journal_id.default_account_id',
        depends=['wizard_id'],
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        compute='_compute_account_id',
        store=True,
        readonly=False,
        check_company=True,
        domain="""[
            ('deprecated', '=', False),
            ('id', '!=', journal_default_account_id),
            ('account_type', 'not in', ('asset_cash', 'off_balance')),
        ]""",
    )
    date = fields.Date(
        compute='_compute_date',
        store=True,
        readonly=False,
    )
    name = fields.Char(
        compute='_compute_name',
        store=True,
        readonly=False,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        compute='_compute_partner_id',
        store=True,
        readonly=False,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
        store=True,
        readonly=False,
    )
    company_id = fields.Many2one(related='wizard_id.company_id')
    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id'])
    company_currency_id = fields.Many2one(related='wizard_id.company_currency_id')
    amount_currency = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_amount_currency',
        store=True,
        readonly=False,
    )
    balance = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_balance',
        store=True,
        readonly=False,
    )
    transaction_currency_id = fields.Many2one(
        related='wizard_id.st_line_id.foreign_currency_id',
        depends=['wizard_id'],
    )
    amount_transaction_currency = fields.Monetary(
        currency_field='transaction_currency_id',
        related='wizard_id.st_line_id.amount_currency',
        depends=['wizard_id'],
    )
    debit = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_balance',
    )
    credit = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_balance',
    )
    force_price_included_taxes = fields.Boolean()
    tax_base_amount_currency = fields.Monetary(
        currency_field='currency_id',
    )

    source_aml_id = fields.Many2one(comodel_name='account.move.line')
    source_aml_move_id = fields.Many2one(
        comodel_name='account.move',
        compute='_compute_source_aml_fields',
        store=True,
        readonly=False,
    )
    source_aml_move_name = fields.Char(
        compute='_compute_source_aml_fields',
        store=True,
        readonly=False,
    )
    tax_repartition_line_id = fields.Many2one(
        comodel_name='account.tax.repartition.line',
        compute='_compute_tax_repartition_line_id',
        store=True,
        readonly=False,
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        compute='_compute_tax_ids',
        store=True,
        readonly=False,
        check_company=True,
    )
    tax_tag_ids = fields.Many2many(
        comodel_name='account.account.tag',
        compute='_compute_tax_tag_ids',
        store=True,
        readonly=False,
    )
    group_tax_id = fields.Many2one(
        comodel_name='account.tax',
        compute='_compute_group_tax_id',
        store=True,
        readonly=False,
    )
    reconcile_model_id = fields.Many2one(comodel_name='account.reconcile.model')
    source_amount_currency = fields.Monetary(currency_field='currency_id')
    source_balance = fields.Monetary(currency_field='company_currency_id')
    source_debit = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_source_balance',
    )
    source_credit = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_source_balance',
    )
    source_rate = fields.Float()

    display_stroked_amount_currency = fields.Boolean(compute='_compute_display_stroked_amount_currency')
    display_stroked_balance = fields.Boolean(compute='_compute_display_stroked_balance')

    partner_currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_partner_info',
    )
    partner_receivable_account_id = fields.Many2one(
        comodel_name='account.account',
        compute='_compute_partner_info',
    )
    partner_payable_account_id = fields.Many2one(
        comodel_name='account.account',
        compute='_compute_partner_info',
    )
    partner_receivable_amount = fields.Monetary(
        currency_field='partner_currency_id',
        compute='_compute_partner_info',
    )
    partner_payable_amount = fields.Monetary(
        currency_field='partner_currency_id',
        compute='_compute_partner_info',
    )

    bank_account = fields.Char(
        compute='_compute_bank_account',
    )
    suggestion_html = fields.Html(
        compute='_compute_suggestion',
        sanitize=False,
    )
    suggestion_amount_currency = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_suggestion',
    )
    suggestion_balance = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_suggestion',
    )
    ref = fields.Char(
        compute='_compute_ref_narration',
        store=True,
        readonly=False,
    )
    narration = fields.Html(
        compute='_compute_ref_narration',
        store=True,
        readonly=False,
    )

    manually_modified = fields.Boolean()

    def _compute_index(self):
        for line in self:
            line.index = uuid.uuid4()

    @api.depends('source_aml_id')
    def _compute_account_id(self):
        for line in self:
            if line.flag in ('aml', 'new_aml', 'liquidity', 'exchange_diff'):
                line.account_id = line.source_aml_id.account_id
            else:
                line.account_id = line.account_id

    @api.depends('source_aml_id')
    def _compute_date(self):
        for line in self:
            if line.flag in ('aml', 'new_aml', 'exchange_diff'):
                line.date = line.source_aml_id.date
            elif line.flag in ('liquidity', 'auto_balance', 'manual', 'early_payment', 'tax_line'):
                line.date = line.wizard_id.st_line_id.date
            else:
                line.date = line.date

    @api.depends('source_aml_id')
    def _compute_name(self):
        for line in self:
            if line.flag in ('aml', 'new_aml', 'liquidity'):
                # In the case the source_aml_id is from a credit note, the aml might not have a name set
                line.name = line.source_aml_id.name or line.source_aml_move_name
            else:
                line.name = line.name

    @api.depends('source_aml_id')
    def _compute_partner_id(self):
        for line in self:
            if line.flag in ('aml', 'new_aml'):
                line.partner_id = line.source_aml_id.partner_id
            elif line.flag in ('liquidity', 'auto_balance', 'manual', 'early_payment', 'tax_line'):
                line.partner_id = line.wizard_id.partner_id
            else:
                line.partner_id = line.partner_id

    @api.depends('source_aml_id')
    def _compute_currency_id(self):
        for line in self:
            if line.flag in ('aml', 'new_aml', 'liquidity', 'exchange_diff'):
                line.currency_id = line.source_aml_id.currency_id
            elif line.flag in ('auto_balance', 'manual', 'early_payment'):
                line.currency_id = line.wizard_id.transaction_currency_id
            else:
                line.currency_id = line.currency_id

    @api.depends('source_aml_id')
    def _compute_balance(self):
        for line in self:
            if line.flag in ('aml', 'liquidity'):
                line.balance = line.source_aml_id.balance
            else:
                line.balance = line.balance

    @api.depends('source_aml_id')
    def _compute_amount_currency(self):
        for line in self:
            if line.flag in ('aml', 'liquidity'):
                line.amount_currency = line.source_aml_id.amount_currency
            else:
                line.amount_currency = line.amount_currency

    @api.depends('balance')
    def _compute_from_balance(self):
        for line in self:
            line.debit = line.balance if line.balance > 0.0 else 0.0
            line.credit = -line.balance if line.balance < 0.0 else 0.0

    @api.depends('source_balance')
    def _compute_from_source_balance(self):
        for line in self:
            line.source_debit = line.source_balance if line.source_balance > 0.0 else 0.0
            line.source_credit = -line.source_balance if line.source_balance < 0.0 else 0.0

    @api.depends('source_aml_id', 'account_id', 'partner_id')
    def _compute_analytic_distribution(self):
        cache = {}
        for line in self:
            if line.flag in ('liquidity', 'aml'):
                line.analytic_distribution = line.source_aml_id.analytic_distribution
            elif line.flag in ('tax_line', 'early_payment'):
                line.analytic_distribution = line.analytic_distribution
            else:
                arguments = frozendict({
                    "partner_id": line.partner_id.id,
                    "partner_category_id": line.partner_id.category_id.ids,
                    "account_prefix": line.account_id.code,
                    "company_id": line.company_id.id,
                })
                if arguments not in cache:
                    cache[arguments] = self.env['account.analytic.distribution.model']._get_distribution(arguments)
                line.analytic_distribution = cache[arguments] or line.analytic_distribution

    @api.depends('source_aml_id')
    def _compute_tax_repartition_line_id(self):
        for line in self:
            if line.flag == 'aml':
                line.tax_repartition_line_id = line.source_aml_id.tax_repartition_line_id
            else:
                line.tax_repartition_line_id = line.tax_repartition_line_id

    @api.depends('source_aml_id')
    def _compute_tax_ids(self):
        for line in self:
            if line.flag == 'aml':
                line.tax_ids = [Command.set(line.source_aml_id.tax_ids.ids)]
            else:
                line.tax_ids = line.tax_ids

    @api.depends('source_aml_id')
    def _compute_tax_tag_ids(self):
        for line in self:
            if line.flag == 'aml':
                line.tax_tag_ids = [Command.set(line.source_aml_id.tax_tag_ids.ids)]
            else:
                line.tax_tag_ids = line.tax_tag_ids

    @api.depends('source_aml_id')
    def _compute_group_tax_id(self):
        for line in self:
            if line.flag == 'aml':
                line.group_tax_id = line.source_aml_id.group_tax_id
            else:
                line.group_tax_id = line.group_tax_id

    @api.depends('currency_id', 'amount_currency', 'source_amount_currency')
    def _compute_display_stroked_amount_currency(self):
        for line in self:
            line.display_stroked_amount_currency = \
                line.flag == 'new_aml' \
                and line.currency_id.compare_amounts(line.amount_currency, line.source_amount_currency) != 0

    @api.depends('currency_id', 'balance', 'source_balance')
    def _compute_display_stroked_balance(self):
        for line in self:
            line.display_stroked_balance = \
                line.flag in ('new_aml', 'exchange_diff') \
                and line.currency_id.compare_amounts(line.balance, line.source_balance) != 0

    @api.depends('flag')
    def _compute_source_aml_fields(self):
        for line in self:
            line.source_aml_move_id = None
            line.source_aml_move_name = None
            if line.flag in ('new_aml', 'liquidity'):
                line.source_aml_move_id = line.source_aml_id.move_id
                line.source_aml_move_name = line.source_aml_id.move_id.name
            elif line.flag == 'aml':
                partials = line.source_aml_id.matched_debit_ids + line.source_aml_id.matched_credit_ids
                all_counterpart_lines = partials.debit_move_id + partials.credit_move_id
                counterpart_lines = all_counterpart_lines - line.source_aml_id - partials.exchange_move_id.line_ids
                if len(counterpart_lines) == 1:
                    line.source_aml_move_id = counterpart_lines.move_id
                    line.source_aml_move_name = counterpart_lines.move_id.name

    @api.depends('wizard_id.form_index', 'partner_id')
    def _compute_partner_info(self):
        for line in self:
            line.partner_receivable_amount = 0.0
            line.partner_payable_amount = 0.0
            line.partner_currency_id = None
            line.partner_receivable_account_id = None
            line.partner_payable_account_id = None

            if not line.partner_id or line.index != line.wizard_id.form_index:
                continue

            line.partner_currency_id = line.company_currency_id
            partner = line.partner_id.with_company(line.wizard_id.company_id)
            common_domain = [('parent_state', '=', 'posted'), ('partner_id', '=', partner.id)]
            line.partner_receivable_account_id = partner.property_account_receivable_id
            if line.partner_receivable_account_id:
                results = self.env['account.move.line']._read_group(
                    domain=expression.AND([common_domain, [('account_id', '=', line.partner_receivable_account_id.id)]]),
                    aggregates=['amount_residual:sum'],
                )
                line.partner_receivable_amount = results[0][0]
            line.partner_payable_account_id = partner.property_account_payable_id
            if line.partner_payable_account_id:
                results = self.env['account.move.line']._read_group(
                    domain=expression.AND([common_domain, [('account_id', '=', line.partner_payable_account_id.id)]]),
                    aggregates=['amount_residual:sum'],
                )
                line.partner_payable_amount = results[0][0]

    @api.depends('flag')
    def _compute_bank_account(self):
        for line in self:
            bank_account = line.wizard_id.st_line_id.partner_bank_id.display_name or line.wizard_id.st_line_id.account_number
            if line.flag == 'liquidity' and bank_account:
                line.bank_account = bank_account
            else:
                line.bank_account = None

    @api.depends('wizard_id.form_index', 'amount_currency', 'balance')
    def _compute_suggestion(self):
        for line in self:
            line.suggestion_html = None
            line.suggestion_amount_currency = None
            line.suggestion_balance = None

            if line.flag != 'new_aml' or line.index != line.wizard_id.form_index:
                continue

            aml = line.source_aml_id
            wizard = line.wizard_id
            residual_amount_before_reco = abs(aml.amount_residual_currency)
            residual_amount_after_reco = abs(aml.amount_residual_currency + line.amount_currency)
            reconciled_amount = residual_amount_before_reco - residual_amount_after_reco
            is_fully_reconciled = aml.currency_id.is_zero(residual_amount_after_reco)
            is_invoice = aml.move_id.is_invoice(include_receipts=True)

            if is_fully_reconciled:
                lines = [
                    _("The invoice %(display_name_html)s with an open amount of %(open_amount)s will be entirely paid by the transaction.")
                    if is_invoice else
                    _("%(display_name_html)s with an open amount of %(open_amount)s will be fully reconciled by the transaction.")
                ]
                partial_amounts = wizard._lines_check_partial_amount(line)
                if partial_amounts:
                    lines.append(
                        _("You might want to record a %(btn_start)spartial payment%(btn_end)s.")
                        if is_invoice else
                        _("You might want to make a %(btn_start)spartial reconciliation%(btn_end)s instead.")
                    )
                    line.suggestion_amount_currency = partial_amounts['amount_currency']
                    line.suggestion_balance = partial_amounts['balance']
            else:
                if is_invoice:
                    lines = [
                        _("The invoice %(display_name_html)s with an open amount of %(open_amount)s will be reduced by %(amount)s."),
                        _("You might want to set the invoice as %(btn_start)sfully paid%(btn_end)s."),
                    ]
                else:
                    lines = [
                        _("%(display_name_html)s with an open amount of %(open_amount)s will be reduced by %(amount)s."),
                        _("You might want to %(btn_start)sfully reconcile%(btn_end)s the document."),
                    ]
                line.suggestion_amount_currency = line.source_amount_currency
                line.suggestion_balance = line.source_balance

            display_name_html = markupsafe.Markup("""
                <button name="action_redirect_to_move"
                        class="btn btn-link p-0 align-baseline fst-italic">%(display_name)s</button>
            """) % {
                'display_name': aml.move_id.display_name,
            }

            extra_text = markupsafe.Markup('<br/>').join(lines) % {
                'amount': formatLang(self.env, reconciled_amount, currency_obj=aml.currency_id),
                'open_amount': formatLang(self.env, residual_amount_before_reco, currency_obj=aml.currency_id),
                'display_name_html': display_name_html,
                'btn_start': markupsafe.Markup(
                    '<button name="action_apply_line_suggestion" class="btn btn-link p-0 align-baseline fst-italic">'),
                'btn_end': markupsafe.Markup('</button>'),
            }
            line.suggestion_html = markupsafe.Markup("""<div class="text-muted">%s</div>""") % extra_text

    @api.depends('flag')
    def _compute_ref_narration(self):
        for line in self:
            if line.flag == 'liquidity':
                line.ref = line.wizard_id.st_line_id.ref
                line.narration = line.wizard_id.st_line_id.narration
            else:
                line.ref = line.narration = None

    def _get_aml_values(self, **kwargs):
        self.ensure_one()
        create_dict = {
            'name': self.name,
            'account_id': self.account_id.id,
            'currency_id': self.currency_id.id,
            'amount_currency': self.amount_currency,
            'balance': self.debit - self.credit,
            'reconcile_model_id': self.reconcile_model_id.id,
            'analytic_distribution': self.analytic_distribution,
            'tax_repartition_line_id': self.tax_repartition_line_id.id,
            'tax_ids': [Command.set(self.tax_ids.ids)],
            'tax_tag_ids': [Command.set(self.tax_tag_ids.ids)],
            'group_tax_id': self.group_tax_id.id,
            **kwargs,
        }
        if self.flag == 'early_payment':
            create_dict['display_type'] = 'epd'
        return create_dict
