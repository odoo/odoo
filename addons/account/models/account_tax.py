from num2words import currency
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import frozendict, groupby, html2plaintext, is_html_empty, split_every, SQL
from odoo.tools.float_utils import float_is_zero, float_repr, float_round, float_compare
from odoo.tools.misc import clean_context
from odoo.tools.translate import html_translate, adapt_translated_field_value, mark_as_copy
from odoo.addons.account.models.taxes_helpers import Compute, sum_and_distribute_amounts_to

from collections import defaultdict
from markupsafe import Markup

import ast
import copy
import math
import re

TYPE_TAX_USE = [
    ('sale', 'Sales'),
    ('purchase', 'Purchases'),
    ('none', 'None'),
]


class AccountTaxGroup(models.Model):
    _name = 'account.tax.group'
    _description = 'Tax Group'
    _order = 'sequence asc, id'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    tax_payable_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        domain="[('account_type', '=', 'liability_payable'), ('non_trade', '=', True)]",
        string='Tax Payable Account',
        help="Tax current account used as a counterpart to the Tax Closing Entry when in favor of the authorities.")
    tax_receivable_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        domain="[('account_type', '=', 'asset_receivable'), ('non_trade', '=', True)]",
        string='Tax Receivable Account',
        help="Tax current account used as a counterpart to the Tax Closing Entry when in favor of the company.")
    advance_tax_payment_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        string='Tax Advance Account',
        help="Downpayments posted on this account will be considered by the Tax Closing Entry.")
    country_id = fields.Many2one(
        string="Country",
        comodel_name='res.country',
        compute='_compute_country_id', store=True, readonly=False, precompute=True,
        help="The country for which this tax group is applicable.",
    )
    country_code = fields.Char(related="country_id.code")
    preceding_subtotal = fields.Char(
        string="Preceding Subtotal",
        help="If set, this value will be used on documents as the label of a subtotal excluding this tax group before displaying it. " \
             "If not set, the tax group will be displayed after the 'Untaxed amount' subtotal.",
        translate=True,
    )
    pos_receipt_label = fields.Char(string='PoS receipt label')

    @api.constrains('tax_payable_account_id', 'tax_receivable_account_id')
    def _constrains_payable_receivable_account(self):
        for tax_group in self:
            if tax_group.tax_payable_account_id and tax_group.tax_payable_account_id.account_type != 'liability_payable':
                raise UserError(self.env._("You must select a payable account for 'Tax Payable Account'."))
            if tax_group.tax_receivable_account_id and tax_group.tax_receivable_account_id.account_type != 'asset_receivable':
                raise UserError(self.env._("You must select a receivable account for 'Tax Receivable Account'."))
            if (
                (tax_group.tax_payable_account_id and not tax_group.tax_payable_account_id.non_trade)
                or (tax_group.tax_receivable_account_id and not tax_group.tax_receivable_account_id.non_trade)
            ):
                raise UserError(self.env._("You must use non-trade accounts for tax groups."))

    @api.depends('company_id')
    def _compute_country_id(self):
        for group in self:
            group.country_id = group.company_id.account_fiscal_country_id or group.company_id.country_id


class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = ['mail.thread']
    _description = 'Tax'
    _order = 'sequence,id'
    _check_company_auto = True
    _rec_names_search = ('name', 'description', 'invoice_label')
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(string='Tax Name', required=True, translate=True, tracking=True, copy=mark_as_copy('name'))
    type_tax_use = fields.Selection(TYPE_TAX_USE, string='Tax Type', required=True, default="sale", tracking=True,
        help="Determines where the tax is selectable. Note: 'None' means a tax can't be used by itself, however it can still be used in a group. 'adjustment' is used to perform tax adjustment.")
    tax_scope = fields.Selection([('service', 'Services'), ('consu', 'Goods')], string="Tax Scope")
    amount_type = fields.Selection(default='percent', string="Tax Computation", required=True, tracking=True,
        selection=[('group', 'Group of Taxes'), ('fixed', 'Fixed'), ('percent', 'Percentage'), ('division', 'Percentage Tax Included')],
        help="""
    - Group of Taxes: The tax is a set of sub taxes.
    - Fixed: The tax amount stays the same whatever the price.
    - Percentage: The tax amount is a % of the price:
        e.g 100 * (1 + 10%) = 110 (not price included)
        e.g 110 / (1 + 10%) = 100 (price included)
    - Percentage Tax Included: The tax amount is a division of the price:
        e.g 180 / (1 - 10%) = 200 (not price included)
        e.g 200 * (1 - 10%) = 180 (price included)
        """)
    fiscal_position_ids = fields.Many2many(
        comodel_name='account.fiscal.position',
        relation='account_fiscal_position_account_tax_rel',
        column1='account_tax_id',
        column2='account_fiscal_position_id',
    )
    original_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='account_tax_alternatives',
        column1='dest_tax_id',  # This Replacement tax
        column2='src_tax_id',  # Domestic Tax to replace
        string="Replaces",
        domain="""[
            ('type_tax_use', '=', type_tax_use),
            ('is_domestic', '=', True),
        ]""",
        ondelete='cascade',
        help="List of taxes to replace when applying any of the stipulated fiscal positions.",
    )
    replacing_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='account_tax_alternatives',
        column1='src_tax_id',  # Domestic Tax to replace
        column2='dest_tax_id',  # This Replacement tax
        readonly=True,
        string="Replaced by",
    )
    display_alternative_taxes_field = fields.Boolean(compute='_compute_display_alternative_taxes_field')
    is_domestic = fields.Boolean(compute='_compute_is_domestic', store=True, precompute=True)
    active = fields.Boolean(default=True, help="Set active to false to hide the tax without removing it.")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    children_tax_ids = fields.Many2many('account.tax',
        'account_tax_filiation_rel', 'parent_tax', 'child_tax',
        check_company=True,
        string='Children Taxes')
    sequence = fields.Integer(required=True, default=1,
        help="The sequence field is used to define order in which the tax lines are applied.")
    amount = fields.Float(required=True, digits=(16, 4), default=0.0, tracking=True)
    description = fields.Html(string='Description', translate=html_translate)
    invoice_label = fields.Char(string='Label on Invoices', translate=True)
    tax_label = fields.Char(compute='_compute_tax_label')
    price_include = fields.Boolean(
        compute='_compute_price_include',
        search='_search_price_include',
        help="Determines whether the price you use on the product and invoices includes this tax.")
    company_price_include = fields.Selection(related="company_id.account_price_include")
    price_include_override = fields.Selection(
        selection=[('tax_included', 'Tax Included'), ('tax_excluded', 'Tax Excluded')],
        string='Included in Price',
        tracking=True,
        help="Overrides the Company's default on whether the price you use on the product and invoices includes this tax."
    )
    include_base_amount = fields.Boolean(string='Affect Base of Subsequent Taxes', default=False, tracking=True,
        help="If set, taxes with a higher sequence than this one will be affected by it, provided they accept it.")
    is_base_affected = fields.Boolean(
        string="Base Affected by Previous Taxes",
        default=True,
        tracking=True,
        help="If set, taxes with a lower sequence might affect this one, provided they try to do it.")
    analytic = fields.Boolean(string="Include in Analytic Cost", help="If set, the amount computed by this tax will be assigned to the same analytic account as the invoice line (if any)")
    tax_group_id = fields.Many2one(
        comodel_name='account.tax.group',
        string="Tax Group",
        compute='_compute_tax_group_id', readonly=False, store=True,
        required=True, precompute=True,
        domain="[('country_id', 'in', (country_id, False))]")
    # Technical field to make the 'tax_exigibility' field invisible if the same named field is set to false in 'res.company' model
    hide_tax_exigibility = fields.Boolean(string='Hide Use Cash Basis Option', related='company_id.tax_exigibility', readonly=True)
    tax_exigibility = fields.Selection(
        [('on_invoice', 'Based on Invoice'),
         ('on_payment', 'Based on Payment'),
        ], string='Tax Exigibility', default='on_invoice',
        help="Based on Invoice: the tax is due as soon as the invoice is validated.\n"
        "Based on Payment: the tax is due as soon as the payment of the invoice is received.")
    cash_basis_transition_account_id = fields.Many2one(string="Cash Basis Transition Account",
        check_company=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        comodel_name='account.account',
        help="Account used to transition the tax amount for cash basis taxes. It will contain the tax amount as long as the original invoice has not been reconciled ; at reconciliation, this amount cancelled on this account and put on the regular tax account.")
    invoice_repartition_line_ids = fields.One2many(
        string="Distribution for Invoices",
        comodel_name="account.tax.repartition.line",
        compute='_compute_invoice_repartition_line_ids', store=True, readonly=False,
        inverse_name="tax_id",
        domain=[('document_type', '=', 'invoice')],
        help="Distribution when the tax is used on an invoice",
    )
    refund_repartition_line_ids = fields.One2many(
        string="Distribution for Refund Invoices",
        comodel_name="account.tax.repartition.line",
        compute='_compute_refund_repartition_line_ids', store=True, readonly=False,
        inverse_name="tax_id",
        domain=[('document_type', '=', 'refund')],
        help="Distribution when the tax is used on a refund",
    )
    repartition_line_ids = fields.One2many(
        string="Distribution",
        comodel_name="account.tax.repartition.line",
        inverse_name="tax_id",
        copy=True,
    )
    country_id = fields.Many2one(
        string="Country",
        comodel_name='res.country',
        compute='_compute_country_id', readonly=False, store=True,
        required=True, precompute=True,
        help="The country for which this tax is applicable.",
    )
    country_code = fields.Char(related='country_id.code', readonly=True)
    company_country_code = fields.Char(
        related='company_id.account_fiscal_country_id.code',
        string="Fiscal Country Code of the Company",
    )
    is_used = fields.Boolean(string="Tax used", compute='_compute_is_used')
    repartition_lines_str = fields.Char(string="Repartition Lines", tracking=True, compute='_compute_repartition_lines_str')
    invoice_legal_notes = fields.Html(string="Legal Notes", translate=True, help="Legal mentions that have to be printed on the invoices.")
    # Technical field depicting if the tax has at least one repartition line with a percentage below 0.
    # Used for the taxes computation to manage the reverse charge taxes having a repartition +100 -100.
    has_negative_factor = fields.Boolean(compute='_compute_has_negative_factor')
    non_deductible_amount = fields.Float(compute='_compute_non_deductible_amount')
    account_move_line_ids = fields.Many2many(
        comodel_name='account.move.line',
        relation='account_move_line_account_tax_rel',
        column1='account_tax_id',
        column2='account_move_line_id',
        copy=False,
        readonly=True,
    )
    account_reconcile_model_line_ids = fields.Many2many(
        comodel_name='account.reconcile.model.line',
        relation='account_reconcile_model_line_account_tax_rel',
        column1='account_tax_id',
        column2='account_reconcile_model_line_id',
        copy=False,
        readonly=True,
    )

    @api.constrains('company_id', 'name', 'type_tax_use', 'tax_scope', 'country_id')
    def _constrains_name(self):
        for taxes in split_every(100, self.ids, self.browse):
            domains = []
            for tax in taxes:
                if tax.type_tax_use != 'none':
                    domains.append([
                        ('company_id', 'child_of', tax.company_id.root_id.id),
                        ('name', '=', tax.name),
                        ('type_tax_use', '=', tax.type_tax_use),
                        ('tax_scope', '=', tax.tax_scope),
                        ('country_id', '=', tax.country_id.id),
                        ('id', '!=', tax.id),
                    ])
            if duplicates := self.sudo().search(Domain.OR(domains)):
                raise ValidationError(
                    self.env._(
                        "Tax names must be unique!\n%(taxes)s",
                        taxes="\n".join(
                            self.env._(
                                "- %(name)s in %(company)s",
                                name=duplicate.name,
                                company=duplicate.company_id.name,
                            )
                            for duplicate in duplicates
                        ),
                    ),
                )

    @api.constrains('tax_group_id')
    def validate_tax_group_id(self):
        for record in self:
            if record.tax_group_id.country_id and record.tax_group_id.country_id != record.country_id:
                raise ValidationError(_("The tax group must have the same country_id as the tax using it."))

    @api.model
    @api.readonly
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        domain = Domain(domain or Domain.TRUE)
        if 'search_default_domestictax' in self.env.context:
            domain &= Domain('fiscal_position_ids', '=', False) | Domain('fiscal_position_ids.is_domestic', '=', True)
        if fp_id := self.env.context.get('dynamic_fiscal_position_id'):
            domain &= Domain('fiscal_position_ids', 'in', [False, int(fp_id)])
        if self.env.context.get('hide_original_tax_ids') and fp_id:
            domain &= Domain('replacing_tax_ids', 'not any', domain) | Domain.custom(
                to_sql=lambda table: SQL(
                    "EXISTS (SELECT 1 FROM %s WHERE %s = %s AND %s = %s)",
                    SQL.identifier('account_tax_alternatives'),
                    SQL.identifier('src_tax_id'),
                    table.id,
                    SQL.identifier('dest_tax_id'),
                    table.id,
                ),
            )
        return super().name_search(name, domain, operator, limit)

    @api.depends('company_id')
    def _compute_country_id(self):
        for tax in self:
            tax.country_id = tax.company_id.account_fiscal_country_id or tax.company_id.country_id or tax.country_id

    @api.depends('company_id', 'country_id')
    def _compute_tax_group_id(self):
        by_country_company = defaultdict(self.browse)
        for tax in self:
            if (
                not tax.tax_group_id
                or tax.tax_group_id.country_id != tax.country_id
                or tax.tax_group_id.company_id != tax.company_id
            ):
                by_country_company[(tax.country_id, tax.company_id)] += tax
        for (country, company), taxes in by_country_company.items():
            taxes.tax_group_id = self.env['account.tax.group'].search([
                *self.env['account.tax.group']._check_company_domain(company),
                ('country_id', '=', country.id),
            ], limit=1) or self.env['account.tax.group'].search([
                *self.env['account.tax.group']._check_company_domain(company),
                ('country_id', '=', False),
            ], limit=1)

    @api.depends('price_include_override')
    def _compute_price_include(self):
        for tax in self:
            tax.price_include = (
                tax.price_include_override == 'tax_included'
                or (tax.company_price_include == 'tax_included'
                    and not tax.price_include_override)
            )

    def _search_price_include(self, operator, value):
        if operator not in ('in', 'not in'):
            return NotImplemented
        assert list(value) == [True]
        tax_value = 'tax_included' if operator == 'in' else 'tax_excluded'
        return [
            '|', ('price_include_override', '=', tax_value),
                '&', ('price_include_override', '=', False),
                        ('company_price_include', '=', tax_value),
        ]

    @api.depends('company_id', 'company_id.domestic_fiscal_position_id', 'fiscal_position_ids')
    def _compute_is_domestic(self):
        for tax in self:
            tax.is_domestic = not tax.fiscal_position_ids or tax.company_id.domestic_fiscal_position_id in tax.fiscal_position_ids

    @api.depends('fiscal_position_ids')
    def _compute_display_alternative_taxes_field(self):
        for tax in self:
            tax.display_alternative_taxes_field = (
                tax.original_tax_ids
                or (
                    tax.fiscal_position_ids
                    and tax.fiscal_position_ids._origin != tax.company_id.domestic_fiscal_position_id  # _origin used to get the actual records
                )
            )

    @api.depends('account_move_line_ids', 'account_reconcile_model_line_ids')
    def _compute_is_used(self):
        used_taxes = set(self.sudo().search([
            ('id', 'in', self.ids),
            '|',
            ('account_move_line_ids', '!=', False),
            ('account_reconcile_model_line_ids', '!=', False),
        ]))
        for tax in self:
            tax.is_used = tax in used_taxes

    @api.depends('is_used', 'repartition_line_ids.account_id', 'repartition_line_ids.sequence', 'repartition_line_ids.factor_percent', 'repartition_line_ids.use_in_tax_closing', 'repartition_line_ids.tag_ids')
    def _compute_repartition_lines_str(self):
        for tax in self:
            repartition_lines_str = tax.repartition_lines_str or ""
            if tax.is_used:
                repartition_line_info = {}
                invoice_sequence = 0
                refund_sequence = 0
                for repartition_line in tax.repartition_line_ids.sorted(key=lambda r: (r.document_type, r.sequence)):
                    # Clean sequence numbers to avoid unnecessary logging when complex
                    # operations are executed such as:
                    #   1. Create a invoice repartition line with a factor of 50%
                    #   2. Delete the invoice line above
                    #   3. Update the last refund repartition line factor to 50%
                    sequence = (invoice_sequence := invoice_sequence + 1) if repartition_line.document_type == 'invoice' else (refund_sequence := refund_sequence + 1)
                    repartition_line_info[(repartition_line.document_type, sequence)] = {
                        _('Factor Percent'): repartition_line.factor_percent,
                        _('Account'): repartition_line.account_id.display_name or _('None'),
                        _('Tax Grids'): repartition_line.tag_ids.mapped('name') or _('None'),
                        _('Use in tax closing'): _('True') if repartition_line.use_in_tax_closing else _('False'),
                    }
                repartition_lines_str = str(repartition_line_info)
            tax.repartition_lines_str = repartition_lines_str

    def _message_log_repartition_lines(self, old_values_str, new_values_str):
        self.ensure_one()
        if not self.is_used:
            return

        old_line_values_dict = ast.literal_eval(old_values_str or '{}')
        new_line_values_dict = ast.literal_eval(new_values_str)

        # Categorize the lines that were added/removed/modified
        modified_lines = [
            (line, old_line_values_dict[line], new_line_values_dict[line])
            for line in old_line_values_dict.keys() & new_line_values_dict.keys()
        ]
        added_and_deleted_lines = [
            (line, self.env._('Removed'), old_line_values_dict[line])
            if line in old_line_values_dict
            else (line, self.env._('New'), new_line_values_dict[line])
            for line in old_line_values_dict.keys() ^ new_line_values_dict.keys()
        ]

        for (document_type, sequence), old_value, new_value in modified_lines:
            diff_keys = [key for key in old_value if old_value[key] != new_value[key]]
            if diff_keys:
                self._track_add(
                    {self.id: {fname: str(old_value[fname]) for fname in diff_keys}},  # everything logged as pure char
                    end_values={self.id: {fname: str(new_value[fname]) for fname in diff_keys}},  # everything logged as pure char
                    fields_info={fname: {'type': 'char', 'string': fname} for fname in diff_keys},
                    body=Markup("<b>{type}</b> {rep} {seq}").format(
                        type=document_type.capitalize(),
                        rep=_('repartition line'),
                        seq=sequence,
                    )
                )
                self._track_finalize()

        for (document_type, sequence), operation, value in added_and_deleted_lines:
            changed = [key for key in value if value[key]]
            if changed:
                self._track_add(
                    {self.id: {fname: False for fname in changed}},
                    end_values={self.id: {fname: str(value[fname]) for fname in changed}},  # everything logged as pure char
                    fields_info={fname: {'type': 'char', 'string': fname} for fname in changed},
                    body=Markup("<b>{op} {type}</b> {rep} {seq}").format(
                        op=operation,
                        type=document_type.capitalize(),
                        rep=_('repartition line'),
                        seq=sequence,
                    )
                )
                self._track_finalize()
        return

    def _track_execute(self, track_init_values, trackings, track_records=None):
        to_update, old_values, new_values = self.browse(), [], []
        super_trackings = {}
        for record in self:
            changes, tracking_values = trackings.get(record.id, (None, None))
            if changes and 'repartition_lines_str' in changes:
                to_update |= record
                repartition_lines_str_track = next((value for value in tracking_values if value.get('field_name') == 'repartition_lines_str'), {})
                old_values.append(repartition_lines_str_track.get('old_value_char'))
                new_values.append(repartition_lines_str_track.get('new_value_char'))
            super_changes = [fname for fname in changes if fname != 'repartition_lines_str']
            super_trackings[record.id] = (super_changes, tracking_values)
        res = super()._track_execute(track_init_values, super_trackings, track_records=track_records)
        for record, old_value, new_value in zip(to_update, old_values, new_values):
            record._message_log_repartition_lines(old_value, new_value)
        return res

    @api.depends('company_id')
    def _compute_invoice_repartition_line_ids(self):
        for tax in self:
            if not tax.invoice_repartition_line_ids:
                tax.invoice_repartition_line_ids = [
                    Command.create({'document_type': 'invoice', 'repartition_type': 'base', 'tag_ids': []}),
                    Command.create({'document_type': 'invoice', 'repartition_type': 'tax', 'tag_ids': []}),
                ]

    @api.depends('company_id')
    def _compute_refund_repartition_line_ids(self):
        for tax in self:
            if not tax.refund_repartition_line_ids:
                tax.refund_repartition_line_ids = [
                    Command.create({'document_type': 'refund', 'repartition_type': 'base', 'tag_ids': []}),
                    Command.create({'document_type': 'refund', 'repartition_type': 'tax', 'tag_ids': []}),
                ]

    @api.depends('invoice_repartition_line_ids.factor', 'invoice_repartition_line_ids.repartition_type')
    def _compute_has_negative_factor(self):
        for tax in self:
            tax_reps = tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
            tax.has_negative_factor = bool(tax_reps.filtered(lambda tax_rep: tax_rep.factor < 0.0))

    @staticmethod
    def _parse_name_search(name):
        """
        Parse the name to search the taxes faster.
        Technical:  0EUM      => 0%E%U%M
                    21M       => 2%1%M%   where the % represents 0, 1 or multiple characters in a SQL 'LIKE' search.
                    21" M"    => 2%1% M%
                    21" M"co  => 2%1% M%c%o%
        Examples:   0EUM      => VAT 0% EU M.
                    21M       => 21% M , 21% EU M, 21% M.Cocont and 21% EX M.
                    21" M"    => 21% M and 21% M.Cocont.
                    21" M"co  => 21% M.Cocont.
        """
        regex = r"(\"[^\"]*\")"
        list_name = re.split(regex, name)
        for i, name in enumerate(list_name.copy()):
            if not name:
                continue
            if re.search(regex, name):
                list_name[i] = "%" + name.replace("%", "_").replace("\"", "") + "%"
            else:
                list_name[i] = '%'.join(re.sub(r"\W+", "", name))
        return ''.join(list_name)

    @api.model
    def _search(self, domain, *args, **kwargs):
        """
        Intercept the search on `name` to allow searching more freely on taxes
        when using `like` or `ilike`.
        """
        def preprocess_name(cond):
            if (
                cond.field_expr in ('name', 'display_name')
                and cond.operator in ('like', 'ilike')
                and isinstance(cond.value, str)
            ):
                return Domain(cond.field_expr, cond.operator, AccountTax._parse_name_search(cond.value))
            return cond
        domain = Domain(domain).map_conditions(preprocess_name)
        return super()._search(domain, *args, **kwargs)

    def _check_repartition_lines(self, lines):
        self.ensure_one()

        base_line = lines.filtered(lambda x: x.repartition_type == 'base')
        if len(base_line) != 1:
            raise ValidationError(_("Invoice and credit note distribution should each contain exactly one line for the base."))

    @api.constrains('invoice_repartition_line_ids', 'refund_repartition_line_ids', 'repartition_line_ids')
    def _validate_repartition_lines(self):
        for record in self:
            # if the tax is an aggregation of its sub-taxes (group) it can have no repartition lines
            if record.amount_type == 'group' and \
                    not record.invoice_repartition_line_ids and \
                    not record.refund_repartition_line_ids:
                continue

            invoice_repartition_line_ids = record.invoice_repartition_line_ids.sorted(lambda l: (l.sequence, l.id))
            refund_repartition_line_ids = record.refund_repartition_line_ids.sorted(lambda l: (l.sequence, l.id))
            record._check_repartition_lines(invoice_repartition_line_ids)
            record._check_repartition_lines(refund_repartition_line_ids)

            if len(invoice_repartition_line_ids) != len(refund_repartition_line_ids):
                raise ValidationError(_("Invoice and credit note distribution should have the same number of lines."))

            if not invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax') or \
                    not refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax'):
                raise ValidationError(_("Invoice and credit note repartition should have at least one tax repartition line."))

            index = 0
            while index < len(invoice_repartition_line_ids):
                inv_rep_ln = invoice_repartition_line_ids[index]
                ref_rep_ln = refund_repartition_line_ids[index]
                if inv_rep_ln.repartition_type != ref_rep_ln.repartition_type or inv_rep_ln.factor_percent != ref_rep_ln.factor_percent:
                    raise ValidationError(_("Invoice and credit note distribution should match (same percentages, in the same order)."))
                index += 1

            tax_reps = invoice_repartition_line_ids.filtered(lambda tax_rep: tax_rep.repartition_type == 'tax')
            total_pos_factor = sum(tax_reps.filtered(lambda tax_rep: tax_rep.factor > 0.0).mapped('factor'))
            if float_compare(total_pos_factor, 1.0, precision_digits=2):
                raise ValidationError(_("Invoice and credit note distribution should have a total factor (+) equals to 100."))
            total_neg_factor = sum(tax_reps.filtered(lambda tax_rep: tax_rep.factor < 0.0).mapped('factor'))
            if total_neg_factor and float_compare(total_neg_factor, -1.0, precision_digits=2):
                raise ValidationError(_("Invoice and credit note distribution should have a total factor (-) equals to 100."))

    @api.constrains('children_tax_ids', 'type_tax_use')
    def _check_children_scope(self):
        for tax in self:
            if tax._has_cycle('children_tax_ids'):
                raise ValidationError(_("Recursion found for tax “%s”.", tax.name))
            if any(
                child.type_tax_use not in ('none', tax.type_tax_use)
                or child.tax_scope not in (tax.tax_scope, False)
                for child in tax.children_tax_ids
            ):
                raise ValidationError(_('The application scope of taxes in a group must be either the same as the group or left empty.'))
            if any(
                child.amount_type == 'group'
                for child in tax.children_tax_ids
            ):
                raise ValidationError(_('Nested group of taxes are not allowed.'))

    @api.constrains('company_id')
    def _check_company_consistency(self):
        if self.env.context.get('from_account_tax_creation') is True:
            # we're creating a new tax, skip usage consistency check as there
            # could not be any usage prior to its creation.
            return
        for company, taxes in groupby(self, lambda tax: tax.company_id):
            if self.env['account.move.line'].search_count([
                '|',
                ('tax_line_id', 'in', [tax.id for tax in taxes]),
                ('tax_ids', 'in', [tax.id for tax in taxes]),
                '!', ('company_id', 'child_of', company.id)
            ], limit=1):
                raise UserError(_("You can't change the company of your tax since there are some journal items linked to it."))

    def _sanitize_vals(self, vals):
        """Normalize the create/write values."""
        sanitized = vals.copy()

        # Wrap plain text in <div> if description has no HTML tags to avoid the padding with automatically added <p>
        if sanitized.get('description'):
            sanitized['description'] = adapt_translated_field_value(
                self.env,
                self._fields["description"],
                sanitized.get('description'),
                lambda lang, v: f"<div>{v}</div>" if not re.search(r'<[^>]+>', v) else v,
            )

        # Allow to provide invoice_repartition_line_ids and refund_repartition_line_ids by dispatching them
        # correctly in the repartition_line_ids
        if 'repartition_line_ids' in sanitized and (
            'invoice_repartition_line_ids' in sanitized
            or 'refund_repartition_line_ids' in sanitized
        ):
            del sanitized['repartition_line_ids']
        for doc_type in ('invoice', 'refund'):
            fname = f"{doc_type}_repartition_line_ids"
            if fname in sanitized:
                repartition = sanitized.setdefault('repartition_line_ids', [])
                for command_vals in sanitized.pop(fname):
                    if command_vals[0] == Command.CREATE:
                        repartition.append(Command.create({'document_type': doc_type, **command_vals[2]}))
                    elif command_vals[0] == Command.UPDATE:
                        repartition.append(Command.update(command_vals[1], {'document_type': doc_type, **command_vals[2]}))
                    else:
                        repartition.append(command_vals)
                sanitized[fname] = []
        return sanitized

    @api.model_create_multi
    def create(self, vals_list):
        self.env.cr.cache.pop('retrieved_tax_map', None)
        context = clean_context(self.env.context)
        context.update({
            'mail_create_nosubscribe': True,  # At create or message_post, do not subscribe the current user to the record thread
            'mail_auto_subscribe_no_notify': True,  # Do no notify users set as followers of the mail thread
            'mail_create_nolog': True,  # At create, do not log the automatic "<Document> created" message
            'from_account_tax_creation': True,  # At create, skip some usage consistency checks
        })
        taxes = super(AccountTax, self.with_context(context)).create([self._sanitize_vals(vals) for vals in vals_list])
        return taxes.with_context(self.env.context)

    def write(self, vals):
        self.env.cr.cache.pop('retrieved_tax_map', None)
        return super().write(self._sanitize_vals(vals))

    @api.depends('type_tax_use', 'tax_scope')
    @api.depends_context('append_fields', 'formatted_display_name')
    def _compute_display_name(self):
        type_tax_uses = dict(self._fields['type_tax_use']._description_selection(self.env))
        scopes = dict(self._fields['tax_scope']._description_selection(self.env))

        needs_markdown = self.env.context.get('formatted_display_name')
        wrapper = "\t--%s--" if needs_markdown else " (%s)"
        fields_to_include = set(self.env.context.get('append_fields') or [])

        for record in self:
            if name := record.name:
                if 'type_tax_use' in fields_to_include and (use := type_tax_uses.get(record.type_tax_use)):
                    name += wrapper % use
                if 'company_id' in fields_to_include and len(self.env.companies) > 1:
                    name += wrapper % record.company_id.display_name
                if needs_markdown and (scope := scopes.get(record.tax_scope)):  # scope is always in the dropdown options, never in the tag
                    name += wrapper % scope
                if record.country_id != record.company_id._accessible_branches()[:1].account_fiscal_country_id:
                    name += wrapper % record.country_code

            record.display_name = name

    @api.depends('name', 'invoice_label')
    def _compute_tax_label(self):
        for tax in self:
            tax.tax_label = tax.invoice_label or tax.name

    @api.depends(
        'invoice_repartition_line_ids.repartition_type',
        'invoice_repartition_line_ids.use_in_tax_closing',
        'invoice_repartition_line_ids.factor_percent',
    )
    def _compute_non_deductible_amount(self):
        for tax in self:
            tax.non_deductible_amount = sum(
                rep_line.factor_percent / 100.0
                for rep_line in tax.invoice_repartition_line_ids
                if rep_line.repartition_type == 'tax' and not rep_line.use_in_tax_closing
            )

    @api.onchange('amount_type')
    def onchange_amount_type(self):
        if self.amount_type != 'group':
            self.children_tax_ids = [(5,)]
        if self.amount_type == 'group':
            self.invoice_label = None

    @api.onchange('price_include')
    def onchange_price_include(self):
        if self.price_include:
            self.include_base_amount = True

    def flatten_taxes_hierarchy(self):
        return self._flatten_taxes_and_sort_them()[0]

    def get_tax_tags(self, is_refund, repartition_type):
        document_type = 'refund' if is_refund else 'invoice'
        return self.repartition_line_ids\
            .filtered(lambda x: x.repartition_type == repartition_type and x.document_type == document_type)\
            .mapped('tag_ids')

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True, include_caba_tags=False, rounding_method=None, document_tax_mode=None):
        """Compute all information required to apply taxes (in self + their children in case of a tax group).
        We consider the sequence of the parent for group of taxes.
        Eg. considering letters as taxes and alphabetic order as sequence::

            [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]

        :param price_unit: The unit price of the line to compute taxes on.
        :param currency: The optional currency in which the price_unit is expressed.
        :param quantity: The optional quantity of the product to compute taxes on.
        :param product: The optional product to compute taxes on.
            Used to get the tags to apply on the lines.

        :param partner: The optional partner compute taxes on.
            Used to retrieve the lang to build strings and for potential extensions.

        :param is_refund: The optional boolean indicating if this is a refund.
        :param handle_price_include: Used when we need to ignore all tax included in price. If False, it means the
            amount passed to this method will be considered as the base of all computations.

        :param include_caba_tags: The optional boolean indicating if CABA tags need to be taken into account.
        :returns:
            ::

                {
                    'total_excluded': 0.0,    # Total without taxes
                    'total_included': 0.0,    # Total with taxes
                    'total_void'    : 0.0,    # Total with those taxes, that don't have an account set
                    'base_tags: : list<int>,  # Tags to apply on the base line
                    'taxes': [{               # One dict for each tax in self and their children
                        'id': int,
                        'name': str,
                        'amount': float,
                        'base': float,
                        'sequence': int,
                        'account_id': int,
                        'refund_account_id': int,
                        'analytic': bool,
                        'price_include': bool,
                        'tax_exigibility': str,
                        'tax_repartition_line_id': int,
                        'group': recordset,
                        'tag_ids': list<int>,
                        'tax_ids': list<int>,
                    }],
                }
        """
        if not self:
            company = self.env.company
        else:
            company = self[0].company_id._accessible_branches()[:1] or self[0].company_id

        # Compute tax details for a single line.
        currency = currency or company.currency_id
        if 'force_price_include' in self.env.context:
            special_mode = 'total_included' if self.env.context['force_price_include'] else 'total_excluded'
        elif not handle_price_include:
            special_mode = 'total_excluded'
        else:
            special_mode = False
        base_line = self._prepare_base_line_for_taxes_computation(
            None,
            partner_id=partner,
            currency_id=currency,
            product_id=product,
            tax_ids=self,
            price_unit=price_unit,
            quantity=quantity,
            is_refund=is_refund,
            special_mode=special_mode,
            document_tax_mode=document_tax_mode,
        )

        if not rounding_method:
            if company.tax_calculation_rounding_method == 'round_per_line':
                rounding_method = 'round_per_line'
            else:
                rounding_method = 'no_round'

        self._add_tax_details([base_line], company, rounding_method=rounding_method)
        self.with_context(
            compute_all_use_raw_base_lines=True,
        )._add_accounting_data_to_base_line_tax_details(base_line, company, include_caba_tags=include_caba_tags)

        tax_details = base_line['tax_details']
        total_void = total_excluded = tax_details['raw_total_excluded_currency']
        total_included = tax_details['raw_total_included_currency']

        # Convert to the 'old' compute_all api.
        taxes = []
        for tax_data in tax_details['taxes_data']:
            tax = tax_data['tax']
            for tax_rep_data in tax_data['tax_reps_data']:
                rep_line = tax_rep_data['tax_rep']
                taxes.append({
                    'id': tax.id,
                    'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
                    'amount': tax_rep_data['tax_amount_currency'],
                    'base': tax_data['raw_base_amount_currency'],
                    'sequence': tax.sequence,
                    'account_id': tax_rep_data['account'].id,
                    'analytic': tax.analytic,
                    'use_in_tax_closing': rep_line.use_in_tax_closing,
                    'is_reverse_charge': tax_data['is_reverse_charge'],
                    'price_include': tax._is_price_included(base_line['document_tax_mode']),
                    'tax_exigibility': tax.tax_exigibility,
                    'tax_repartition_line_id': rep_line.id,
                    'group': tax_data['group'],
                    'tag_ids': tax_rep_data['tax_tags'].ids,
                    'tax_ids': tax_rep_data['taxes'].ids,
                })
                if not rep_line.account_id:
                    total_void += tax_rep_data['tax_amount_currency']

        if self.env.context.get('round_base', True):
            total_excluded = currency.round(total_excluded)
            total_included = currency.round(total_included)

        return {
            'base_tags': base_line['tax_tag_ids'].ids,
            'taxes': taxes,
            'total_excluded': total_excluded,
            'total_included': total_included,
            'total_void': total_void,
        }

    def _filter_taxes_by_company(self, company=None):
        """ Filter taxes by the given company
            It goes through the company hierarchy until a tax is found
        """
        if not self:
            return self

        company = company or self.env.company
        taxes = self.env['account.tax']
        while not taxes and company:
            taxes = self.filtered(lambda t: t.company_id == company)
            company = company.sudo().parent_id
        return taxes

    @api.model
    def _fix_tax_included_price(self, price, prod_taxes, line_taxes, document_tax_mode=None):
        """Subtract tax amount from price when corresponding "price included" taxes do not apply"""
        # FIXME get currency in param?
        prod_taxes = prod_taxes._origin
        line_taxes = line_taxes._origin
        incl_tax = prod_taxes.filtered(lambda tax: tax not in line_taxes and tax._is_price_included(document_tax_mode))
        if incl_tax:
            return incl_tax.compute_all(price)['total_excluded']
        return price

    @api.model
    def _fix_tax_included_price_company(self, price, prod_taxes, line_taxes, company_id, document_tax_mode=None):
        if company_id:
            #To keep the same behavior as in _compute_tax_id
            prod_taxes = prod_taxes.filtered(lambda tax: tax.company_id == company_id)
            line_taxes = line_taxes.filtered(lambda tax: tax.company_id == company_id)
        return self._fix_tax_included_price(price, prod_taxes, line_taxes, document_tax_mode)

    def _get_description_plaintext(self):
        self.ensure_one()
        if is_html_empty(self.description):
            return ''
        return html2plaintext(self.description)

    @api.ondelete(at_uninstall=False)
    def unlink_except_tax_used(self):
        if any(self.mapped('is_used')):
            raise ValidationError(self.env._("You cannot delete taxes that are currently in use. Consider archiving them instead."))

    @api.model
    def _import_retrieve_tax_from_account_default_tax(self, tax_values):
        account = tax_values.get('account')
        if not account or not account.tax_ids:
            return

        return {
            'criteria': [{
                'domain': [('id', 'in', account.tax_ids.ids)],
            }],
        }

    @api.model
    def _import_retrieve_tax_from_predicted_tax(self, tax_values):
        predicted_tax_ids = tax_values.get('predicted_tax_ids')
        if not predicted_tax_ids:
            return

        return {
            'criteria': [{
                'domain': [('id', 'in', predicted_tax_ids.ids)],
            }],
        }

    @api.model
    def _import_retrieve_tax_from_price_include_exclude(self, tax_values):
        price_include = tax_values.get('price_include')
        fiscal_position = tax_values.get('fiscal_position')

        fpos_domain = []
        if fiscal_position:
            fpos_domain = Domain('fiscal_position_ids', '=', fiscal_position.id)
            if fiscal_position.is_domestic:
                fpos_domain |= Domain('fiscal_position_ids', '=', False)

        criteria = []
        if not price_include:
            if fiscal_position:
                criteria.append({'domain': [('price_include', '=', False)] + fpos_domain})
            criteria.append({'domain': [('price_include', '=', False)]})
        if price_include is None or price_include:
            if fiscal_position:
                criteria.append({'domain': [('price_include', '=', True)] + fpos_domain})
            criteria.append({'domain': [('price_include', '=', True)]})

        return {'criteria': criteria}

    @api.model
    def _import_retrieve_tax(self, search_plan, company, tax_values_list):
        cache = self.env.cr.cache.setdefault('retrieved_tax_map', {}).setdefault(company.id, {})

        static_domain = Domain(self._check_company_domain(company))
        for tax_values in tax_values_list:
            if tax_values.get('tax'):
                continue
            tax_domain = (
               Domain('amount_type', '=', tax_values['amount_type'])
               & Domain('type_tax_use', '=', tax_values['type_tax_use'])
               & Domain('amount', '=', tax_values['amount'])
            )
            orders = ['sequence', 'id']
            if name := tax_values.get('name'):
                tax_domain &= Domain('name', '=', name)
            if tax_exigibility := tax_values.get('tax_exigibility'):
                tax_domain &= Domain('tax_exigibility', '=', tax_exigibility)
            if (
                (ubl_cii_tax_category_code := tax_values.get('ubl_cii_tax_category_code'))
                and 'ubl_cii_tax_category_code' in self._fields
            ):
                tax_domain &= Domain('ubl_cii_tax_category_code', 'in', (ubl_cii_tax_category_code, False))
                orders.insert(0, 'ubl_cii_tax_category_code')

            for plan in search_plan:
                tax = None
                plan_values = plan(tax_values)
                if not plan_values:
                    continue

                for criteria in plan_values['criteria']:
                    domain = criteria.get('domain')
                    search_method = criteria.get('search_method')
                    if domain:
                        domain = tax_domain & Domain(domain)
                        cache_key = repr(domain.optimize(self.env['account.tax']))
                    else:
                        cache_key = criteria.get('cache_key')
                        if cache_key:
                            cache_key = (cache_key, str(tax_domain))

                    # Look at the cache if the value has already been tested with this key.
                    if cache_key and cache_key in cache:
                        if tax := cache[cache_key]:
                            tax_values['tax'] = tax
                            break
                        else:
                            continue

                    if domain:
                        full_domain = static_domain & Domain(domain)
                        tax = self.search(full_domain, order=','.join(orders), limit=1)
                    elif search_method:
                        tax = search_method({
                            **criteria,
                            'static_domain': tax_domain & static_domain,
                        })

                    if cache_key:
                        cache[cache_key] = tax
                    if tax:
                        tax_values['tax'] = tax
                        break

                if tax:
                    break


class AccountTaxRepartitionLine(models.Model):
    _name = 'account.tax.repartition.line'
    _description = "Tax Repartition Line"
    _order = 'document_type, repartition_type, sequence, id'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    factor_percent = fields.Float(
        string="%",
        default=100,
        digits=(16, 12),
        required=True,
        help="Factor to apply on the journal items generated from this distribution line, in percents",
    )
    factor = fields.Float(string="Factor Ratio", compute="_compute_factor", help="Factor to apply on the journal items generated from this distribution line")
    repartition_type = fields.Selection(string="Based On", selection=[('base', 'Base'), ('tax', 'of tax')], required=True, default='tax', help="Base on which the factor will be applied.")
    document_type = fields.Selection(string="Related to", selection=[('invoice', 'Invoice'), ('refund', 'Refund')], required=True)
    account_id = fields.Many2one(string="Account",
        comodel_name='account.account',
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'off_balance'))]",
        check_company=True,
        index='btree_not_null',
        help="Account on which to post the tax amount")
    account_active = fields.Boolean(related='account_id.active', string="Account Active")
    tag_ids = fields.Many2many(string="Tax Grids", comodel_name='account.account.tag', domain=[('applicability', '=', 'taxes')], copy=True, ondelete='restrict')
    tax_id = fields.Many2one(comodel_name='account.tax', index='btree_not_null', ondelete='cascade', check_company=True)
    company_id = fields.Many2one(string="Company", comodel_name='res.company', related="tax_id.company_id", store=True, help="The company this distribution line belongs to.")
    sequence = fields.Integer(string="Sequence", default=1,
        help="The order in which distribution lines are displayed and matched. For refunds to work properly, invoice distribution lines should be arranged in the same order as the credit note distribution lines they correspond to.")
    use_in_tax_closing = fields.Boolean(
        string="Tax Closing Entry",
        compute='_compute_use_in_tax_closing', store=True, readonly=False, precompute=True,
    )

    tag_ids_domain = fields.Json(string="tag domain", help="Dynamic domain used for the tag that can be set on tax", compute="_compute_tag_ids_domain")

    @api.depends('company_id.multi_vat_foreign_country_ids', 'company_id.account_fiscal_country_id')
    def _compute_tag_ids_domain(self):
        for rep_line in self:
            allowed_country_ids = (False, rep_line.company_id.account_fiscal_country_id.id, *rep_line.company_id.multi_vat_foreign_country_ids.ids,)
            rep_line.tag_ids_domain = [('applicability', '=', 'taxes'), ('country_id', 'in', allowed_country_ids)]

    @api.depends('account_id', 'repartition_type')
    def _compute_use_in_tax_closing(self):
        for rep_line in self:
            rep_line.use_in_tax_closing = (
                rep_line.repartition_type == 'tax'
                and rep_line.account_id
                and rep_line.account_id.internal_group not in ('income', 'expense')
            )

    @api.depends('factor_percent')
    def _compute_factor(self):
        for record in self:
            record.factor = record.factor_percent / 100.0

    @api.onchange('repartition_type')
    def _onchange_repartition_type(self):
        if self.repartition_type == 'base':
            self.account_id = None

    def _get_aml_target_tax_account(self, force_caba_exigibility=False):
        """ Get the default tax account to set on a business line.

        :return: An account.account record or an empty recordset.
        """
        self.ensure_one()
        if not force_caba_exigibility and self.tax_id.tax_exigibility == 'on_payment' and not self.env.context.get('caba_no_transition_account'):
            return self.tax_id.cash_basis_transition_account_id
        else:
            return self.account_id
