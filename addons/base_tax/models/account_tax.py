"""
Standalone Tax Computation Engine
=================================

Copy of the tax computation models from ``account/models/account_tax.py``,
extracted for use by ``base_order`` and other modules that need tax computation
without the full accounting stack.

Phase 1: standalone copy.  Phase 2 (future) will make ``account`` depend on
this module and remove the duplication.

Models:
    AccountTaxGroup             — tax grouping for display and reporting
    AccountTax                  — tax definition, rate computation, base line preparation
    AccountTaxRepartitionLine   — tax distribution factors

Key API (order-facing):
    _prepare_base_line_for_taxes_computation()
    _add_tax_details_in_base_lines()
    _round_base_lines_tax_details()
    _get_tax_totals_summary()
    compute_all()
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.numbers.float_utils import (
    float_compare,
    float_is_zero,
    float_repr,
    float_round,
)
from odoo.tools import frozendict, html2plaintext, is_html_empty
from odoo.tools.misc import clean_context
from odoo.tools.translate import html_translate

from collections import defaultdict
from itertools import batched
import copy
import re


TYPE_TAX_USE = [
    ('sale', 'Sales'),
    ('purchase', 'Purchases'),
    ('none', 'None'),
]


# ════════════════════════════════════════════════════════════════════════
# TAX GROUP
# ════════════════════════════════════════════════════════════════════════

class AccountTaxGroup(models.Model):
    _name = 'account.tax.group'
    _description = 'Tax Group'
    _order = 'sequence asc, id'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    country_id = fields.Many2one(
        string="Country",
        comodel_name='res.country',
        compute='_compute_country_id',
        store=True,
        readonly=False,
        precompute=True,
        help="The country for which this tax group is applicable.",
    )
    country_code = fields.Char(related="country_id.code")
    preceding_subtotal = fields.Char(
        string="Preceding Subtotal",
        help=(
            "If set, this value will be used on documents as the label of a "
            "subtotal excluding this tax group before displaying it. "
            "If not set, the tax group will be displayed after the "
            "'Untaxed amount' subtotal."
        ),
        translate=True,
    )
    pos_receipt_label = fields.Char(string='PoS receipt label')

    @api.depends('company_id')
    def _compute_country_id(self):
        for group in self:
            if 'account_fiscal_country_id' in group.company_id._fields:
                group.country_id = (
                    group.company_id.account_fiscal_country_id
                    or group.company_id.country_id
                )
            else:
                group.country_id = group.company_id.country_id


# ════════════════════════════════════════════════════════════════════════
# TAX
# ════════════════════════════════════════════════════════════════════════

class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = ['mail.thread']
    _description = 'Tax'
    _order = 'sequence,id'
    _check_company_auto = True
    _rec_names_search = ['name', 'description', 'invoice_label']
    _check_company_domain = models.check_company_domain_parent_of

    # ─── Core Fields ──────────────────────────────────────────────────

    name = fields.Char(
        string='Tax Name',
        required=True,
        translate=True,
        tracking=True,
    )
    type_tax_use = fields.Selection(
        TYPE_TAX_USE,
        string='Tax Type',
        required=True,
        default="sale",
        tracking=True,
        help=(
            "Determines where the tax is selectable. Note: 'None' means a tax "
            "can't be used by itself, however it can still be used in a group."
        ),
    )
    tax_scope = fields.Selection(
        [('service', 'Services'), ('consu', 'Goods')],
        string="Tax Scope",
        help="Restrict the use of taxes to a type of product.",
    )
    amount_type = fields.Selection(
        default='percent',
        string="Tax Computation",
        required=True,
        tracking=True,
        selection=[
            ('group', 'Group of Taxes'),
            ('fixed', 'Fixed'),
            ('percent', 'Percentage'),
            ('division', 'Percentage Tax Included'),
        ],
        help="""
    - Group of Taxes: The tax is a set of sub taxes.
    - Fixed: The tax amount stays the same whatever the price.
    - Percentage: The tax amount is a % of the price:
        e.g 100 * (1 + 10%) = 110 (not price included)
        e.g 110 / (1 + 10%) = 100 (price included)
    - Percentage Tax Included: The tax amount is a division of the price:
        e.g 180 / (1 - 10%) = 200 (not price included)
        e.g 200 * (1 - 10%) = 180 (price included)
        """,
    )
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the tax without removing it.",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    children_tax_ids = fields.Many2many(
        'account.tax',
        'account_tax_filiation_rel',
        'parent_tax',
        'child_tax',
        check_company=True,
        string='Children Taxes',
    )
    sequence = fields.Integer(
        required=True,
        default=1,
        help="The sequence field is used to define order in which the tax lines are applied.",
    )
    amount = fields.Float(required=True, digits=(16, 4), default=0.0, tracking=True)
    description = fields.Html(string='Description', translate=html_translate)
    invoice_label = fields.Char(string='Label on Invoices', translate=True)
    tax_label = fields.Char(compute='_compute_tax_label')

    # ─── Price Include ────────────────────────────────────────────────

    price_include = fields.Boolean(
        compute='_compute_price_include',
        search='_search_price_include',
        help="Determines whether the price you use on the product and invoices includes this tax.",
    )
    company_price_include = fields.Selection(
        selection=[('tax_included', 'Tax Included'), ('tax_excluded', 'Tax Excluded')],
        compute='_compute_company_price_include',
    )
    price_include_override = fields.Selection(
        selection=[('tax_included', 'Tax Included'), ('tax_excluded', 'Tax Excluded')],
        string='Included in Price',
        tracking=True,
        help=(
            "Overrides the Company's default on whether the price you use on "
            "the product and invoices includes this tax."
        ),
    )
    include_base_amount = fields.Boolean(
        string='Affect Base of Subsequent Taxes',
        default=False,
        tracking=True,
        help="If set, taxes with a higher sequence than this one will be affected by it, provided they accept it.",
    )
    is_base_affected = fields.Boolean(
        string="Base Affected by Previous Taxes",
        default=True,
        tracking=True,
        help="If set, taxes with a lower sequence might affect this one, provided they try to do it.",
    )

    # ─── Tax Group & Repartition ──────────────────────────────────────

    tax_group_id = fields.Many2one(
        comodel_name='account.tax.group',
        string="Tax Group",
        compute='_compute_tax_group_id',
        readonly=False,
        store=True,
        required=True,
        precompute=True,
        domain="[('country_id', 'in', (country_id, False))]",
    )
    invoice_repartition_line_ids = fields.One2many(
        string="Distribution for Invoices",
        comodel_name="account.tax.repartition.line",
        compute='_compute_invoice_repartition_line_ids',
        store=True,
        readonly=False,
        inverse_name="tax_id",
        domain=[('document_type', '=', 'invoice')],
        help="Distribution when the tax is used on an invoice",
    )
    refund_repartition_line_ids = fields.One2many(
        string="Distribution for Refund Invoices",
        comodel_name="account.tax.repartition.line",
        compute='_compute_refund_repartition_line_ids',
        store=True,
        readonly=False,
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

    # ─── Country ──────────────────────────────────────────────────────

    country_id = fields.Many2one(
        string="Country",
        comodel_name='res.country',
        compute='_compute_country_id',
        readonly=False,
        store=True,
        required=True,
        precompute=True,
        help="The country for which this tax is applicable.",
    )
    country_code = fields.Char(related='country_id.code', readonly=True)

    # ─── Reverse Charge Detection ─────────────────────────────────────

    has_negative_factor = fields.Boolean(compute='_compute_has_negative_factor')

    # ─── Constraints ──────────────────────────────────────────────────

    @api.constrains('company_id', 'name', 'type_tax_use', 'tax_scope', 'country_id')
    def _constrains_name(self):
        for taxes in map(self.browse, batched(self.ids, 100)):
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
            if total_pos_factor and float_compare(total_pos_factor, 1.0, precision_digits=2):
                raise ValidationError(_("Invoice and credit note distribution should have a total factor (+) equals to 100."))
            total_neg_factor = sum(tax_reps.filtered(lambda tax_rep: tax_rep.factor < 0.0).mapped('factor'))
            if total_neg_factor and float_compare(total_neg_factor, -1.0, precision_digits=2):
                raise ValidationError(_("Invoice and credit note distribution should have a total factor (-) equals to 100."))

    def _check_repartition_lines(self, lines):
        self.ensure_one()
        base_line = lines.filtered(lambda x: x.repartition_type == 'base')
        if len(base_line) != 1:
            raise ValidationError(_("Invoice and credit note distribution should each contain exactly one line for the base."))

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

    # ─── Name Search ──────────────────────────────────────────────────

    @api.model
    @api.readonly
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        # Simplified version without fiscal position filtering (available in account module).
        return super().name_search(name, domain or Domain.TRUE, operator, limit)

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
        """Intercept the search on ``name`` to allow searching more freely on taxes."""
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

    # ─── Compute Methods ──────────────────────────────────────────────

    @api.depends('company_id')
    def _compute_country_id(self):
        for tax in self:
            if 'account_fiscal_country_id' in tax.company_id._fields:
                tax.country_id = (
                    tax.company_id.account_fiscal_country_id
                    or tax.company_id.country_id
                    or tax.country_id
                )
            else:
                tax.country_id = tax.company_id.country_id or tax.country_id

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

    @api.depends('company_id')
    def _compute_company_price_include(self):
        has_field = 'account_price_include' in self.env['res.company']._fields
        for tax in self:
            tax.company_price_include = (
                tax.company_id.account_price_include if has_field else False
            )

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
        if 'account_price_include' not in self.env['res.company']._fields:
            return [('price_include_override', '=', tax_value)]
        return [
            '|', ('price_include_override', '=', tax_value),
                '&', ('price_include_override', '=', False),
                        ('company_price_include', '=', tax_value),
        ]

    @api.depends('company_id')
    def _compute_invoice_repartition_line_ids(self):
        for tax in self:
            if not tax.invoice_repartition_line_ids:
                tax.invoice_repartition_line_ids = [
                    Command.create({'document_type': 'invoice', 'repartition_type': 'base'}),
                    Command.create({'document_type': 'invoice', 'repartition_type': 'tax'}),
                ]

    @api.depends('company_id')
    def _compute_refund_repartition_line_ids(self):
        for tax in self:
            if not tax.refund_repartition_line_ids:
                tax.refund_repartition_line_ids = [
                    Command.create({'document_type': 'refund', 'repartition_type': 'base'}),
                    Command.create({'document_type': 'refund', 'repartition_type': 'tax'}),
                ]

    @api.depends('invoice_repartition_line_ids.factor', 'invoice_repartition_line_ids.repartition_type')
    def _compute_has_negative_factor(self):
        for tax in self:
            tax_reps = tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
            tax.has_negative_factor = bool(tax_reps.filtered(lambda tax_rep: tax_rep.factor < 0.0))

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
                if needs_markdown and (scope := scopes.get(record.tax_scope)):
                    name += wrapper % scope
                # Check fiscal country (falls back to company country without account module)
                branch = record.company_id._accessible_branches()[:1]
                fiscal_country = (
                    branch.account_fiscal_country_id
                    if 'account_fiscal_country_id' in branch._fields
                    else branch.country_id
                )
                if record.country_id != fiscal_country:
                    name += wrapper % record.country_code

            record.display_name = name

    @api.depends('name', 'invoice_label')
    def _compute_tax_label(self):
        for tax in self:
            tax.tax_label = tax.invoice_label or tax.name

    # ─── CRUD ─────────────────────────────────────────────────────────

    def _sanitize_vals(self, vals):
        """Normalize the create/write values."""
        sanitized = vals.copy()

        # Wrap plain text in <div> if description has no HTML tags
        if sanitized.get('description') and not re.search(r'<[^>]+>', sanitized['description']):
            sanitized['description'] = f"<div>{sanitized['description']}</div>"

        # Allow to provide invoice_repartition_line_ids and refund_repartition_line_ids
        # by dispatching them correctly in the repartition_line_ids
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
        context = clean_context(self.env.context)
        context.update({
            'mail_create_nosubscribe': True,
            'mail_auto_subscribe_no_notify': True,
            'mail_create_nolog': True,
        })
        taxes = super(AccountTax, self.with_context(context)).create([
            self._sanitize_vals(vals) for vals in vals_list
        ])
        return taxes

    def write(self, vals):
        return super().write(self._sanitize_vals(vals))

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for tax, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", tax.name)
        return vals_list

    # ─── Onchanges ────────────────────────────────────────────────────

    @api.onchange('amount')
    def onchange_amount(self):
        if self.amount_type in ('percent', 'division') and self.amount != 0.0 and not self.invoice_label:
            self.invoice_label = "{0:.4g}%".format(self.amount)

    @api.onchange('amount_type')
    def onchange_amount_type(self):
        if self.amount_type != 'group':
            self.children_tax_ids = [Command.clear()]
        if self.amount_type == 'group':
            self.invoice_label = None

    @api.onchange('price_include')
    def onchange_price_include(self):
        if self.price_include:
            self.include_base_amount = True

    # ─────────────────────────────────────────────────────────────────
    # HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js / account_tax.py)
    #
    # TAXES COMPUTATION
    # ─────────────────────────────────────────────────────────────────

    def _eval_taxes_computation_prepare_product_fields(self):
        """ Get the fields to create the evaluation context from the product for the taxes computation.

        [!] Only added python-side.

        :return: A set of fields to be extracted from the product to evaluate the taxes computation.
        """
        return set()

    @api.model
    def _eval_taxes_computation_prepare_product_default_values(self, field_names):
        """ Prepare the default values for the product according the fields passed as parameter.

        [!] Only added python-side.

        :param field_names: A set of fields returned by '_eval_taxes_computation_get_product_fields'.
        :return: A mapping <field_name> => <field_info>.
        """
        default_value_map = {
            'integer': 0,
            'float': 0.0,
            'monetary': 0.0,
        }
        product_fields_values = {}
        for field_name in field_names:
            field = self.env['product.product']._fields[field_name]
            product_fields_values[field_name] = {
                'type': field.type,
                'default_value': default_value_map[field.type],
            }
        return product_fields_values

    @api.model
    def _eval_taxes_computation_prepare_product_values(self, default_product_values, product=None):
        """ Convert the product passed as parameter to a dictionary.

        [!] Only added python-side.

        :param default_product_values:  The default product values.
        :param product:                 An optional product.product record.
        :return:                        The values representing the product.
        """
        product = product and product.sudo()
        product_values = {}
        for field_name, field_info in default_product_values.items():
            product_values[field_name] = product and product[field_name] or field_info['default_value']
        return product_values

    def _eval_taxes_computation_turn_to_product_values(self, product=None):
        """ Helper purely in Python to prepare product values in one call.

        [!] Only added python-side.

        :param product: An optional product.product record.
        :return:        The values representing the product.
        """
        product_fields = self._eval_taxes_computation_prepare_product_fields()
        default_product_values = self._eval_taxes_computation_prepare_product_default_values(product_fields)
        return self._eval_taxes_computation_prepare_product_values(
            default_product_values=default_product_values,
            product=product,
        )

    def _eval_taxes_computation_prepare_product_uom_fields(self):
        """ Get the fields to create the evaluation context from the product uom.

        [!] Only added python-side.

        :return: A set of fields to be extracted from the product uom.
        """
        return set()

    @api.model
    def _eval_taxes_computation_prepare_product_uom_default_values(self, field_names):
        """ Prepare the default values for the product uom.

        [!] Only added python-side.

        :param field_names: A set of fields returned by '_eval_taxes_computation_get_product_uom_fields'.
        :return: A mapping <field_name> => <field_info>.
        """
        default_value_map = {
            'integer': 0,
            'float': 0.0,
            'monetary': 0.0,
        }
        product_uom_fields_values = {}
        for field_name in field_names:
            field = self.env['uom.uom']._fields[field_name]
            product_uom_fields_values[field_name] = {
                'type': field.type,
                'default_value': default_value_map[field.type],
            }
        return product_uom_fields_values

    @api.model
    def _eval_taxes_computation_prepare_product_uom_values(self, default_product_uom_values, product_uom=None):
        """ Convert the product uom passed as parameter to a dictionary.

        [!] Only added python-side.

        :param default_product_uom_values:  The default product values.
        :param product_uom:                 An optional product.uom record.
        :return:                            The values representing the product uom.
        """
        product_uom = product_uom and product_uom.sudo()
        product_uom_values = {}
        for field_name, field_info in default_product_uom_values.items():
            product_uom_values[field_name] = product_uom and product_uom[field_name] or field_info['default_value']
        return product_uom_values

    def _eval_taxes_computation_turn_to_product_uom_values(self, product_uom=None):
        """ Helper purely in Python to prepare product uom values in one call.

        [!] Only added python-side.

        :param product_uom: An optional product.uom record.
        :return:            The values representing the product uom.
        """
        product_uom_fields = self._eval_taxes_computation_prepare_product_uom_fields()
        default_product_uom_values = self._eval_taxes_computation_prepare_product_uom_default_values(product_uom_fields)
        return self._eval_taxes_computation_prepare_product_uom_values(
            default_product_uom_values=default_product_uom_values,
            product_uom=product_uom,
        )

    # ─────────────────────────────────────────────────────────────────
    # TAX FLATTENING & BATCHING
    # ─────────────────────────────────────────────────────────────────

    def _flatten_taxes_and_sort_them(self):
        """ Flattens the taxes contained in this recordset, returning all the
        children at the bottom of the hierarchy, in a recordset, ordered by sequence.
          Eg. considering letters as taxes and alphabetic order as sequence :
          [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :return: A tuple <sorted_taxes, group_per_tax>.
        """
        def sort_key(tax):
            return tax.sequence, tax.id or None

        group_per_tax = {}
        sorted_taxes = self.env['account.tax']
        for tax in self.sorted(key=sort_key):
            if tax.amount_type == 'group':
                children = tax.children_tax_ids.sorted(key=sort_key)
                sorted_taxes |= children
                for child in children:
                    group_per_tax[child.id] = tax
            else:
                sorted_taxes |= tax
        return sorted_taxes, group_per_tax

    def _batch_for_taxes_computation(self, special_mode=False, filter_tax_function=None):
        """ Group the current taxes all together like price-included percent taxes or division taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param special_mode:        The special mode: False, 'total_excluded' or 'total_included'.
        :param filter_tax_function: Optional function to filter out some taxes.
        :return: A dictionary containing batch_per_tax, group_per_tax, sorted_taxes.
        """
        sorted_taxes, group_per_tax = self._flatten_taxes_and_sort_them()
        if filter_tax_function:
            sorted_taxes = sorted_taxes.filtered(filter_tax_function)

        results = {
            'batch_per_tax': {},
            'group_per_tax': group_per_tax,
            'sorted_taxes': sorted_taxes,
        }

        # Group them per batch.
        batch = self.env['account.tax']
        is_base_affected = False
        for tax in reversed(results['sorted_taxes']):
            if batch:
                same_batch = (
                    tax.amount_type == batch[0].amount_type
                    and (special_mode or tax.price_include == batch[0].price_include)
                    and tax.include_base_amount == batch[0].include_base_amount
                    and (
                        (tax.include_base_amount and not is_base_affected)
                        or not tax.include_base_amount
                    )
                )
                if not same_batch:
                    for batch_tax in batch:
                        results['batch_per_tax'][batch_tax.id] = batch
                    batch = self.env['account.tax']

            is_base_affected = tax.is_base_affected
            batch |= tax

        if batch:
            for batch_tax in batch:
                results['batch_per_tax'][batch_tax.id] = batch
        return results

    # ─────────────────────────────────────────────────────────────────
    # TAX AMOUNT EVALUATION
    # ─────────────────────────────────────────────────────────────────

    def _propagate_extra_taxes_base(self, tax, taxes_data, special_mode=False):
        """ Propagate extra base amounts between taxes depending on configuration.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param tax:             The tax for which we need to propagate the tax.
        :param taxes_data:      The computed values for taxes so far.
        :param special_mode:    The special mode: False, 'total_excluded' or 'total_included'.
        """
        def get_tax_before():
            for tax_before in self:
                if tax_before in taxes_data[tax.id]['batch']:
                    break
                yield tax_before

        def get_tax_after():
            for tax_after in reversed(list(self)):
                if tax_after in taxes_data[tax.id]['batch']:
                    break
                yield tax_after

        def add_extra_base(other_tax, sign):
            tax_amount = taxes_data[tax.id]['tax_amount']
            if 'tax_amount' not in taxes_data[other_tax.id]:
                taxes_data[other_tax.id]['extra_base_for_tax'] += sign * tax_amount
            taxes_data[other_tax.id]['extra_base_for_base'] += sign * tax_amount

        if tax.price_include:
            if special_mode in (False, 'total_included'):
                if tax.include_base_amount:
                    for other_tax in get_tax_after():
                        if not other_tax.is_base_affected:
                            add_extra_base(other_tax, -1)
                else:
                    for other_tax in get_tax_after():
                        add_extra_base(other_tax, -1)
                for other_tax in get_tax_before():
                    add_extra_base(other_tax, -1)
            else:  # special_mode == 'total_excluded'
                if tax.include_base_amount:
                    for other_tax in get_tax_after():
                        if other_tax.is_base_affected:
                            add_extra_base(other_tax, 1)

        elif not tax.price_include:
            if special_mode in (False, 'total_excluded'):
                if tax.include_base_amount:
                    for other_tax in get_tax_after():
                        if other_tax.is_base_affected:
                            add_extra_base(other_tax, 1)
            else:  # special_mode == 'total_included'
                if not tax.include_base_amount:
                    for other_tax in get_tax_after():
                        add_extra_base(other_tax, -1)
                for other_tax in get_tax_before():
                    add_extra_base(other_tax, -1)

    def _eval_tax_amount_fixed_amount(self, batch, raw_base, evaluation_context):
        """ Eval the tax amount for fixed taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        if self.amount_type == 'fixed':
            sign = -1 if evaluation_context['price_unit'] < 0.0 else 1
            return sign * evaluation_context['quantity'] * self.amount

    def _eval_tax_amount_price_included(self, batch, raw_base, evaluation_context):
        """ Eval the tax amount for price-included taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        self.ensure_one()
        if self.amount_type == 'percent':
            total_percentage = sum(tax.amount for tax in batch) / 100.0
            to_price_excluded_factor = 1 / (1 + total_percentage) if total_percentage != -1 else 0.0
            return raw_base * to_price_excluded_factor * self.amount / 100.0

        if self.amount_type == 'division':
            return raw_base * self.amount / 100.0

    def _eval_tax_amount_price_excluded(self, batch, raw_base, evaluation_context):
        """ Eval the tax amount for price-excluded taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        self.ensure_one()
        if self.amount_type == 'percent':
            return raw_base * self.amount / 100.0

        if self.amount_type == 'division':
            total_percentage = sum(tax.amount for tax in batch) / 100.0
            incl_base_multiplicator = 1.0 if total_percentage == 1.0 else 1 - total_percentage
            return raw_base * self.amount / 100.0 / incl_base_multiplicator

    # ─────────────────────────────────────────────────────────────────
    # PRIMARY TAX COMPUTATION: _get_tax_details
    # ─────────────────────────────────────────────────────────────────

    def _get_tax_details(
        self,
        price_unit,
        quantity,
        precision_rounding=0.01,
        rounding_method='round_per_line',
        product=None,
        product_uom=None,
        special_mode=False,
        manual_tax_amounts=None,
        filter_tax_function=None,
    ):
        """ Compute the tax/base amounts for the current taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param price_unit:          The price unit of the line.
        :param quantity:            The quantity of the line.
        :param precision_rounding:  The rounding precision for 'round_per_line'.
        :param rounding_method:     'round_per_line' or 'round_globally'.
        :param product:             The product of the line.
        :param product_uom:         The product uom of the line.
        :param special_mode:        False, 'total_excluded' or 'total_included'.
        :param manual_tax_amounts:  TO BE REMOVED IN MASTER.
        :param filter_tax_function: Optional function to filter out some taxes.
        :return: A dict containing total_excluded, total_included, taxes_data.
        """
        def add_tax_amount_to_results(tax, tax_amount):
            taxes_data[tax.id]['tax_amount'] = tax_amount
            if rounding_method == 'round_per_line':
                taxes_data[tax.id]['tax_amount'] = float_round(taxes_data[tax.id]['tax_amount'], precision_rounding=precision_rounding)
            if tax.has_negative_factor:
                reverse_charge_taxes_data[tax.id]['tax_amount'] = -taxes_data[tax.id]['tax_amount']
            sorted_taxes._propagate_extra_taxes_base(tax, taxes_data, special_mode=special_mode)

        def eval_tax_amount(tax_amount_function, tax):
            is_already_computed = 'tax_amount' in taxes_data[tax.id]
            if is_already_computed:
                return

            tax_amount = tax_amount_function(
                taxes_data[tax.id]['batch'],
                raw_base + taxes_data[tax.id]['extra_base_for_tax'],
                evaluation_context,
            )
            if tax_amount is not None:
                add_tax_amount_to_results(tax, tax_amount)

        def prepare_tax_extra_data(tax, **kwargs):
            if tax.has_negative_factor:
                price_include = False
            elif special_mode == 'total_included':
                price_include = True
            elif special_mode == 'total_excluded':
                price_include = False
            else:
                price_include = tax.price_include
            return {
                **kwargs,
                'tax': tax,
                'price_include': price_include,
                'extra_base_for_tax': 0.0,
                'extra_base_for_base': 0.0,
            }

        # Flatten the taxes, order them and filter them if necessary.
        batching_results = self._batch_for_taxes_computation(special_mode=special_mode, filter_tax_function=filter_tax_function)
        sorted_taxes = batching_results['sorted_taxes']
        taxes_data = {}
        reverse_charge_taxes_data = {}
        for tax in sorted_taxes:
            taxes_data[tax.id] = prepare_tax_extra_data(
                tax,
                group=batching_results['group_per_tax'].get(tax.id),
                batch=batching_results['batch_per_tax'][tax.id],
            )
            if tax.has_negative_factor:
                reverse_charge_taxes_data[tax.id] = {
                    **taxes_data[tax.id],
                    'is_reverse_charge': True,
                }

        raw_base = quantity * price_unit
        if rounding_method == 'round_per_line':
            raw_base = float_round(raw_base, precision_rounding=precision_rounding)

        evaluation_context = {
            'product': sorted_taxes._eval_taxes_computation_turn_to_product_values(product=product),
            'uom': sorted_taxes._eval_taxes_computation_turn_to_product_uom_values(product_uom=product_uom),
            'price_unit': price_unit,
            'quantity': quantity,
            'raw_base': raw_base,
            'special_mode': special_mode,
        }

        # Fixed taxes first (could affect subsequent price-included batches).
        for tax in reversed(sorted_taxes):
            eval_tax_amount(tax._eval_tax_amount_fixed_amount, tax)

        # Then price-included taxes in reverse order.
        for tax in reversed(sorted_taxes):
            if taxes_data[tax.id]['price_include']:
                eval_tax_amount(tax._eval_tax_amount_price_included, tax)

        # Then price-excluded taxes in normal order.
        for tax in sorted_taxes:
            if not taxes_data[tax.id]['price_include']:
                eval_tax_amount(tax._eval_tax_amount_price_excluded, tax)

        # Mark the base to be computed in the descending order.
        subsequent_taxes = self.env['account.tax']
        for tax in reversed(sorted_taxes):
            tax_data = taxes_data[tax.id]
            if 'tax_amount' not in tax_data:
                continue

            # Base amount.
            total_tax_amount = sum(taxes_data[other_tax.id]['tax_amount'] for other_tax in tax_data['batch'])
            total_tax_amount += sum(
                reverse_charge_taxes_data[other_tax.id]['tax_amount']
                for other_tax in taxes_data[tax.id]['batch']
                if other_tax.has_negative_factor
            )
            base = raw_base + tax_data['extra_base_for_base']
            if tax_data['price_include'] and special_mode in (False, 'total_included'):
                base -= total_tax_amount
            tax_data['base'] = base

            # Subsequent taxes.
            tax_data['taxes'] = self.env['account.tax']
            if tax.include_base_amount:
                tax_data['taxes'] |= subsequent_taxes

            # Reverse charge.
            if tax.has_negative_factor:
                reverse_charge_tax_data = reverse_charge_taxes_data[tax.id]
                reverse_charge_tax_data['base'] = base
                reverse_charge_tax_data['taxes'] = tax_data['taxes']

            if tax.is_base_affected:
                subsequent_taxes |= tax

        taxes_data_list = []
        for tax_data in taxes_data.values():
            if 'tax_amount' in tax_data:
                taxes_data_list.append(tax_data)
                tax = tax_data['tax']
                if tax.has_negative_factor:
                    taxes_data_list.append(reverse_charge_taxes_data[tax.id])

        if taxes_data_list:
            total_excluded = taxes_data_list[0]['base']
            tax_amount = sum(tax_data['tax_amount'] for tax_data in taxes_data_list)
            total_included = total_excluded + tax_amount
        else:
            total_included = total_excluded = raw_base

        return {
            'total_excluded': total_excluded,
            'total_included': total_included,
            'taxes_data': [
                {
                    'tax': tax_data['tax'],
                    'taxes': tax_data['taxes'],
                    'group': batching_results['group_per_tax'].get(tax_data['tax'].id) or self.env['account.tax'],
                    'batch': batching_results['batch_per_tax'][tax_data['tax'].id],
                    'tax_amount': tax_data['tax_amount'],
                    'price_include': tax_data['price_include'],
                    'base_amount': tax_data['base'],
                    'is_reverse_charge': tax_data.get('is_reverse_charge', False),
                }
                for tax_data in taxes_data_list
            ],
        }

    # ─────────────────────────────────────────────────────────────────
    # MAPPING PRICE_UNIT
    # ─────────────────────────────────────────────────────────────────

    @api.model
    def _adapt_price_unit_to_another_taxes(self, price_unit, product, original_taxes, new_taxes, product_uom=None):
        """ Compute a new price unit corresponding to the new taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param price_unit:      The original price_unit.
        :param product:         The product.
        :param original_taxes:  A recordset of taxes from where you come from.
        :param new_taxes:       A recordset of the taxes you are mapping to.
        :param product_uom:     The product uom.
        :return:                The price_unit after mapping of taxes.
        """
        if original_taxes == new_taxes or False in original_taxes.mapped('price_include'):
            return price_unit

        # Find the price unit without tax.
        taxes_computation = original_taxes._get_tax_details(
            price_unit,
            1.0,
            rounding_method='round_globally',
            product=product,
            product_uom=product_uom,
        )
        price_unit = taxes_computation['total_excluded']

        # Find the new price unit after applying the price included taxes.
        taxes_computation = new_taxes._get_tax_details(
            price_unit,
            1.0,
            rounding_method='round_globally',
            product=product,
            product_uom=product_uom,
            special_mode='total_excluded',
        )
        delta = sum(x['tax_amount'] for x in taxes_computation['taxes_data'] if x['tax'].price_include)
        return price_unit + delta

    # ─────────────────────────────────────────────────────────────────
    # EXTRA TAX DATA SERIALIZATION
    # ─────────────────────────────────────────────────────────────────

    @api.model
    def _export_base_line_extra_tax_data(self, base_line):
        """ Export extra tax values into a JSON-serializable dict.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_line: A base line generated by '_prepare_base_line_for_taxes_computation'.
        :return: A dictionary to be stored into the 'extra_tax_data' field.
        """
        results = {}
        if base_line['computation_key']:
            results['computation_key'] = base_line['computation_key']

        store_source_data = False
        if base_line['manual_total_excluded_currency'] is not None:
            results['manual_total_excluded_currency'] = base_line['manual_total_excluded_currency']
            store_source_data = True
        if base_line['manual_total_excluded'] is not None:
            results['manual_total_excluded'] = base_line['manual_total_excluded']
            store_source_data = True
        if base_line['manual_tax_amounts']:
            results['manual_tax_amounts'] = base_line['manual_tax_amounts']
            store_source_data = True

        if store_source_data:
            results.update({
                'currency_id': base_line['currency_id'].id,
                'price_unit': base_line['price_unit'],
                'discount': base_line['discount'],
                'quantity': base_line['quantity'],
                'rate': base_line['rate'],
            })
        return results

    @api.model
    def _import_base_line_extra_tax_data(self, base_line, extra_tax_data):
        """ Import 'extra_tax_data' JSON value into the base line.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_line:       A base line generated by '_prepare_base_line_for_taxes_computation'.
        :param extra_tax_data:  The value stored in the 'extra_tax_data' field.
        :return:                The values to be added into the base line.
        """
        results = {}
        if extra_tax_data and extra_tax_data.get('computation_key'):
            results['computation_key'] = extra_tax_data['computation_key']

        manual_tax_amounts = extra_tax_data.get('manual_tax_amounts') or {} if extra_tax_data else None
        sorted_taxes = base_line['tax_ids']._flatten_taxes_and_sort_them()[0]
        if (
            extra_tax_data
            and extra_tax_data.get('manual_tax_amounts')
            and base_line['currency_id'].id == extra_tax_data['currency_id']
            and base_line['currency_id'].compare_amounts(base_line['price_unit'], extra_tax_data['price_unit']) == 0
            and base_line['currency_id'].compare_amounts(base_line['discount'], extra_tax_data['discount']) == 0
            and base_line['currency_id'].compare_amounts(base_line['quantity'], extra_tax_data['quantity']) == 0
            and all(str(tax.id) in extra_tax_data['manual_tax_amounts'] for tax in sorted_taxes)
        ):
            results['price_unit'] = extra_tax_data['price_unit']

            if base_line['rate'] and extra_tax_data.get('rate'):
                delta_rate = base_line['rate'] / extra_tax_data['rate']
            else:
                delta_rate = 1.0

            if 'manual_total_excluded_currency' in extra_tax_data:
                results['manual_total_excluded_currency'] = extra_tax_data['manual_total_excluded_currency']
            if 'manual_total_excluded' in extra_tax_data:
                results['manual_total_excluded'] = extra_tax_data['manual_total_excluded'] / delta_rate

            if manual_tax_amounts:
                results['manual_tax_amounts'] = {}
                for tax_id_str, amounts in extra_tax_data['manual_tax_amounts'].items():
                    results['manual_tax_amounts'][tax_id_str] = dict(amounts)
                    if 'tax_amount' in amounts:
                        results['manual_tax_amounts'][tax_id_str]['tax_amount'] /= delta_rate
                    if 'base_amount' in amounts:
                        results['manual_tax_amounts'][tax_id_str]['base_amount'] /= delta_rate

        return results

    @api.model
    def _reverse_quantity_base_line_extra_tax_data(self, extra_tax_data):
        """ Reverse all sign in extra_tax_data using the quantity.

        [!] Only added python-side.

        :param extra_tax_data: The manual taxes data stored on records.
        :return: The extra_tax_data but reversed.
        """
        if not extra_tax_data:
            return None

        new_extra_tax_data = copy.deepcopy(extra_tax_data)
        for field in ('quantity', 'manual_total_excluded_currency', 'manual_total_excluded'):
            if new_extra_tax_data.get(field):
                new_extra_tax_data[field] *= -1
        if new_extra_tax_data.get('manual_tax_amounts'):
            for current_manual_tax_amounts in new_extra_tax_data['manual_tax_amounts'].values():
                for suffix in ('_currency', ''):
                    for prefix in ('base', 'tax'):
                        field = f'{prefix}_amount{suffix}'
                        if current_manual_tax_amounts.get(field):
                            current_manual_tax_amounts[field] *= -1
        return new_extra_tax_data

    def _turn_base_line_is_refund_flag_off(self, base_line):
        """ Reverse the sign of the quantity plus all data in tax details.

        [!] Only added python-side.

        :param base_line: The base_line.
        :return: The base_line that is no longer a refund line.
        """
        if not base_line['is_refund']:
            return base_line

        new_base_line = {
            **base_line,
            'quantity': -base_line['quantity'],
            'is_refund': False,
        }
        tax_details = new_base_line['tax_details']
        new_tax_details = new_base_line['tax_details'] = {
            f'{prefix}{field}{suffix}': -tax_details[f'{prefix}{field}{suffix}']
            for prefix in ('raw_', '')
            for field in ('total_excluded', 'total_included')
            for suffix in ('_currency', '')
        }
        for suffix in ('_currency', ''):
            field = f'delta_total_excluded{suffix}'
            new_tax_details[field] = -tax_details[field]

        new_tax_details['taxes_data'] = new_taxes_data = []
        for tax_data in tax_details['taxes_data']:
            new_tax_data = {**tax_data}
            for prefix in ('raw_', ''):
                for suffix in ('_currency', ''):
                    for field in ('base_amount', 'tax_amount'):
                        field = f'{prefix}{field}{suffix}'
                        new_tax_data[field] = -tax_data[field]
            new_taxes_data.append(new_tax_data)

        return new_base_line

    @api.model
    def _turn_base_lines_is_refund_flag_off(self, base_lines):
        """ Reverse the sign of the quantity plus all data in tax details.

        [!] Only added python-side.

        :param base_lines: The base_lines.
        :return: The base_lines that are no longer refund lines.
        """
        return [self._turn_base_line_is_refund_flag_off(base_line) for base_line in base_lines]

    # ─────────────────────────────────────────────────────────────────
    # BASE LINE PREPARATION
    # ─────────────────────────────────────────────────────────────────

    @api.model
    def _get_base_line_field_value_from_record(self, record, field, extra_values, fallback, from_base_line=False):
        """ Helper to extract a default value for a record or something looking like a record.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param record:          A record or a dict or a falsy value.
        :param field:           The name of the field to extract.
        :param extra_values:    The extra kwargs passed in addition of 'record'.
        :param fallback:        The value to return if not found.
        :param from_base_line:  Indicate if the value has to be retrieved from the base_line.
        :return:                The field value corresponding to 'field'.
        """
        need_origin = isinstance(fallback, models.Model)
        if field in extra_values:
            value = extra_values[field] or fallback
        elif isinstance(record, models.Model) and field in record._fields and not from_base_line:
            value = record[field]
        elif isinstance(record, dict):
            value = record.get(field, fallback)
        else:
            value = fallback
        if need_origin:
            value = value._origin
        return value

    @api.model
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        """ Convert any representation of a business object into a base line dictionary.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param record:  A record or a dictionary.
        :param kwargs:  The extra values to override.
        :return:        A dictionary representing a base line.
        """
        def load(field, fallback):
            return self._get_base_line_field_value_from_record(record, field, kwargs, fallback)

        currency = (
            load('currency_id', None)
            or load('company_currency_id', None)
            or load('company_id', self.env['res.company']).currency_id
            or self.env['res.currency']
        )

        base_line = {
            **kwargs,
            'record': record,
            'id': load('id', 0),

            # Basic fields:
            'product_id': load('product_id', self.env['product.product']),
            'product_uom_id': load('product_uom_id', self.env['uom.uom']),
            'tax_ids': load('tax_ids', self.env['account.tax']),
            'price_unit': load('price_unit', 0.0),
            'quantity': load('quantity', 0.0),
            'discount': load('discount', 0.0),
            'currency_id': currency,

            # The special_mode for the taxes computation:
            'special_mode': kwargs.get('special_mode') or False,

            # A special typing of base line for some custom behavior:
            'special_type': kwargs.get('special_type') or False,

            # Rate for foreign currency → local currency conversion.
            'rate': load('rate', 1.0),

            # Function to filter out some taxes during evaluation.
            'filter_tax_function': kwargs.get('filter_tax_function') or None,

            # ===== Accounting stuff =====

            # The sign of the business object regarding its accounting balance.
            'sign': load('sign', 1.0),

            # If the document is a refund or not.
            'is_refund': load('is_refund', False),

            # Extra fields for tax lines generation (account_id=False when account module not installed):
            'partner_id': load('partner_id', self.env['res.partner']),
            'account_id': load('account_id', False),
            'analytic_distribution': load('analytic_distribution', None),
        }

        extra_tax_data = self._import_base_line_extra_tax_data(base_line, load('extra_tax_data', {}) or {})
        base_line.update({
            'computation_key': kwargs.get('computation_key') or extra_tax_data.get('computation_key'),
            'manual_total_excluded_currency': kwargs.get('manual_total_excluded_currency') or extra_tax_data.get('manual_total_excluded_currency'),
            'manual_total_excluded': kwargs.get('manual_total_excluded') or extra_tax_data.get('manual_total_excluded'),
            'manual_tax_amounts': kwargs.get('manual_tax_amounts') or extra_tax_data.get('manual_tax_amounts'),
        })
        if 'price_unit' in extra_tax_data:
            base_line['price_unit'] = extra_tax_data['price_unit']

        # Propagate custom values.
        if record and isinstance(record, dict):
            for k, v in record.items():
                if k.startswith('_') and k not in base_line:
                    base_line[k] = v

        return base_line

    # ─────────────────────────────────────────────────────────────────
    # ADD TAX DETAILS TO BASE LINES
    # ─────────────────────────────────────────────────────────────────

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        """ Perform the taxes computation for the base line and add it under 'tax_details'.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_line:       A base line generated by '_prepare_base_line_for_taxes_computation'.
        :param company:         The company owning the base line.
        :param rounding_method: The rounding method to be used.
        """
        rounding_method = rounding_method or (
            company.tax_calculation_rounding_method
            if 'tax_calculation_rounding_method' in company._fields
            else 'round_per_line'
        )
        price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        taxes_computation = base_line['tax_ids']._get_tax_details(
            price_unit=price_unit_after_discount,
            quantity=base_line['quantity'],
            precision_rounding=base_line['currency_id'].rounding,
            rounding_method=rounding_method,
            product=base_line['product_id'],
            product_uom=base_line['product_uom_id'],
            special_mode=base_line['special_mode'],
            filter_tax_function=base_line['filter_tax_function'],
        )

        # Only python side for professional with reverse charge
        if base_line['special_type'] == 'non_deductible':
            taxes_data = taxes_computation['taxes_data']
            taxes_computation['taxes_data'] = []
            for tax_data in taxes_data:
                if not tax_data.get('is_reverse_charge'):
                    taxes_computation['taxes_data'].append(tax_data)
                else:
                    taxes_computation['total_included'] -= tax_data['tax_amount']

        rate = base_line['rate']
        tax_details = base_line['tax_details'] = {
            'raw_total_excluded_currency': taxes_computation['total_excluded'],
            'raw_total_excluded': taxes_computation['total_excluded'] / rate if rate else 0.0,
            'raw_total_included_currency': taxes_computation['total_included'],
            'raw_total_included': taxes_computation['total_included'] / rate if rate else 0.0,
            'taxes_data': [],
        }
        if rounding_method == 'round_per_line':
            tax_details['raw_total_excluded'] = company.currency_id.round(tax_details['raw_total_excluded'])
            tax_details['raw_total_included'] = company.currency_id.round(tax_details['raw_total_included'])
        for tax_data in taxes_computation['taxes_data']:
            tax_amount = tax_data['tax_amount'] / rate if rate else 0.0
            base_amount = tax_data['base_amount'] / rate if rate else 0.0
            if rounding_method == 'round_per_line':
                tax_amount = company.currency_id.round(tax_amount)
                base_amount = company.currency_id.round(base_amount)
            tax_details['taxes_data'].append({
                **tax_data,
                'raw_tax_amount_currency': tax_data['tax_amount'],
                'raw_tax_amount': tax_amount,
                'raw_base_amount_currency': tax_data['base_amount'],
                'raw_base_amount': base_amount,
            })

    @api.model
    def _add_tax_details_in_base_lines(self, base_lines, company):
        """ Shortcut to call '_add_tax_details_in_base_line' on multiple base lines.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:  A list of base lines.
        :param company:     The company owning the base lines.
        """
        for base_line in base_lines:
            self._add_tax_details_in_base_line(base_line, company)

    # ─────────────────────────────────────────────────────────────────
    # ROUNDING & DISTRIBUTION
    # ─────────────────────────────────────────────────────────────────

    @api.model
    def _normalize_target_factors(self, target_factors):
        """ Normalize factors to have a distribution summing to 1.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param target_factors:  A list of dict containing at least 'factor'.
        :return:                A list of tuple <index, normalized_factor>.
        """
        factors = [(i, abs(target_factor['factor'])) for i, target_factor in enumerate(target_factors)]
        factors.sort(key=lambda x: x[1], reverse=True)
        sum_of_factors = sum(x[1] for x in factors)
        return [(i, factor / sum_of_factors if sum_of_factors else 1 / len(factors)) for i, factor in factors]

    @api.model
    def _distribute_delta_amount_smoothly(self, precision_digits, delta_amount, target_factors):
        """ Distribute 'delta_amount' across the factors.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param precision_digits:    The decimal places of the delta.
        :param delta_amount:        The delta amount to be distributed.
        :param target_factors:      A list of dict containing at least 'factor'.
        :return:                    A list of floats, one per element in 'target_factors'.
        """
        precision_rounding = float(f"1e-{precision_digits}")
        amounts_to_distribute = [0.0] * len(target_factors)
        if float_is_zero(delta_amount, precision_digits=precision_digits):
            return amounts_to_distribute

        sign = -1 if delta_amount < 0.0 else 1
        nb_of_errors = round(abs(delta_amount / precision_rounding))
        remaining_errors = nb_of_errors

        # Distribute using the factor first.
        factors = self._normalize_target_factors(target_factors)
        for i, factor in factors:
            if not remaining_errors:
                break

            nb_of_amount_to_distribute = min(
                round(factor * nb_of_errors),
                remaining_errors,
            )
            remaining_errors -= nb_of_amount_to_distribute
            amount_to_distribute = sign * nb_of_amount_to_distribute * precision_rounding
            amounts_to_distribute[i] += amount_to_distribute

        # Distribute the remaining cents across the factors.
        for i in range(remaining_errors):
            amounts_to_distribute[factors[i][0]] += sign * precision_rounding

        return amounts_to_distribute

    @api.model
    def _round_tax_details_tax_amounts(self, base_lines, company, mode='mixed'):
        """ Dispatch the delta in tax amounts across the tax details for 'round_globally'.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:  A list of base lines.
        :param company:     The company owning the base lines.
        :param mode:        'excluded', 'included', or 'mixed'.
        """
        def grouping_function(base_line, tax_data):
            if not tax_data:
                return
            return {
                'tax': tax_data['tax'],
                'currency': base_line['currency_id'],
                'is_refund': base_line['is_refund'],
                'is_reverse_charge': tax_data['is_reverse_charge'],
                'price_include': tax_data['price_include'],
                'computation_key': base_line['computation_key'],
            }

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue

            price_include = grouping_key['price_include']
            currency = grouping_key['currency']
            for delta_currency_indicator, delta_currency in (
                ('_currency', currency),
                ('', company.currency_id),
            ):
                # Tax amount.
                raw_total_tax_amount = values[f'target_tax_amount{delta_currency_indicator}']
                rounded_raw_total_tax_amount = delta_currency.round(raw_total_tax_amount)
                total_tax_amount = values[f'tax_amount{delta_currency_indicator}']
                delta_total_tax_amount = rounded_raw_total_tax_amount - total_tax_amount

                if not delta_currency.is_zero(delta_total_tax_amount):
                    target_factors = [
                        {
                            'factor': tax_data[f'raw_tax_amount{delta_currency_indicator}'],
                            'tax_data': tax_data,
                        }
                        for _base_line, taxes_data in values['base_line_x_taxes_data']
                        for tax_data in taxes_data
                    ]
                    amounts_to_distribute = self._distribute_delta_amount_smoothly(
                        precision_digits=delta_currency.decimal_places,
                        delta_amount=delta_total_tax_amount,
                        target_factors=target_factors,
                    )
                    for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                        tax_data = target_factor['tax_data']
                        tax_data[f'tax_amount{delta_currency_indicator}'] += amount_to_distribute

                # Base amount.
                raw_total_base_amount = values[f'target_base_amount{delta_currency_indicator}']
                if (mode == 'mixed' and price_include) or mode == 'included':
                    raw_total_amount = raw_total_base_amount + raw_total_tax_amount
                    rounded_raw_total_amount = delta_currency.round(raw_total_amount)
                    total_amount = values[f'base_amount{delta_currency_indicator}'] + total_tax_amount + delta_total_tax_amount
                    delta_total_base_amount = rounded_raw_total_amount - total_amount
                elif (mode == 'mixed' and not price_include) or mode == 'excluded':
                    rounded_raw_total_base_amount = delta_currency.round(raw_total_base_amount)
                    total_base_amount = values[f'base_amount{delta_currency_indicator}']
                    delta_total_base_amount = rounded_raw_total_base_amount - total_base_amount

                if not delta_currency.is_zero(delta_total_base_amount):
                    target_factors = [
                        {
                            'factor': tax_data[f'raw_base_amount{delta_currency_indicator}'],
                            'tax_data': tax_data,
                        }
                        for _base_line, taxes_data in values['base_line_x_taxes_data']
                        for tax_data in taxes_data
                    ]
                    amounts_to_distribute = self._distribute_delta_amount_smoothly(
                        precision_digits=delta_currency.decimal_places,
                        delta_amount=delta_total_base_amount,
                        target_factors=target_factors,
                    )
                    for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                        tax_data = target_factor['tax_data']
                        tax_data[f'base_amount{delta_currency_indicator}'] += amount_to_distribute

    @api.model
    def _round_tax_details_base_lines(self, base_lines, company, mode='mixed'):
        """ Additional global rounding for price-included / price-excluded taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:  A list of base lines.
        :param company:     The company owning the base lines.
        :param mode:        'excluded', 'included', or 'mixed'.
        """
        def grouping_function(base_line, tax_data):
            return {
                'currency': base_line['currency_id'],
                'is_refund': base_line['is_refund'],
                'computation_key': base_line['computation_key'],
            }

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            current_mode = mode
            if mode == 'mixed':
                current_mode = 'included'
                for base_line, taxes_data in values['base_line_x_taxes_data']:
                    if any(not tax_data['price_include'] for tax_data in taxes_data):
                        current_mode = 'excluded'
                        break

            currency = grouping_key['currency']
            for delta_currency_indicator, delta_currency in (
                ('_currency', currency),
                ('', company.currency_id),
            ):
                if current_mode == 'excluded':
                    raw_total_excluded = values[f'target_total_excluded{delta_currency_indicator}']
                    if not raw_total_excluded:
                        continue

                    rounded_raw_total_excluded = delta_currency.round(raw_total_excluded)
                    total_excluded = values[f'total_excluded{delta_currency_indicator}']
                    delta_total_excluded = rounded_raw_total_excluded - total_excluded
                    target_factors = [
                        {
                            'factor': base_line['tax_details'][f'raw_total_excluded{delta_currency_indicator}'],
                            'base_line': base_line,
                        }
                        for base_line, _taxes_data in values['base_line_x_taxes_data']
                    ]
                else:
                    raw_total_included = (
                        values[f'target_total_excluded{delta_currency_indicator}']
                        + values[f'target_tax_amount{delta_currency_indicator}']
                    )
                    if not raw_total_included:
                        continue

                    rounded_raw_total_included = delta_currency.round(raw_total_included)
                    total_included = (
                        values[f'total_excluded{delta_currency_indicator}']
                        + values[f'tax_amount{delta_currency_indicator}']
                    )
                    delta_total_excluded = rounded_raw_total_included - total_included
                    target_factors = [
                        {
                            'factor': base_line['tax_details'][f'raw_total_included{delta_currency_indicator}'],
                            'base_line': base_line,
                        }
                        for base_line, _taxes_data in values['base_line_x_taxes_data']
                    ]

                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=delta_currency.decimal_places,
                    delta_amount=delta_total_excluded,
                    target_factors=target_factors,
                )
                for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                    base_line = target_factor['base_line']
                    base_line['tax_details'][f'delta_total_excluded{delta_currency_indicator}'] += amount_to_distribute

    @api.model
    def _round_tax_details_tax_amounts_from_tax_lines(self, base_lines, company, tax_lines):
        """ If tax lines are provided, the totals will be aggregated according them.

        [!] Only added python-side.

        :param base_lines:  A list of base lines.
        :param company:     The company owning the base lines.
        :param tax_lines:   An optional list of tax lines. No-op if None.
        """
        if not tax_lines:
            return

        total_per_tax_line_key = defaultdict(lambda: {
            'currency': None,
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
        })
        for tax_line in tax_lines:
            tax_rep = tax_line['tax_repartition_line_id']
            sign = tax_line['sign']
            tax = tax_rep.tax_id
            currency = tax_line['currency_id']
            tax_line_key = (tax.id, currency.id, tax_rep.document_type == 'refund')
            total_per_tax_line_key[tax_line_key]['currency'] = currency
            total_per_tax_line_key[tax_line_key]['tax_amount_currency'] += sign * tax_line['amount_currency']
            total_per_tax_line_key[tax_line_key]['tax_amount'] += sign * tax_line['balance']

        def grouping_function(base_line, tax_data):
            if not tax_data:
                return
            return {
                'tax': tax_data['tax'],
                'currency': base_line['currency_id'],
                'is_refund': base_line['is_refund'],
            }

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue

            currency = grouping_key['currency']
            tax_line_key = (grouping_key['tax'].id, currency.id, grouping_key['is_refund'])
            if tax_line_key not in total_per_tax_line_key:
                continue

            for delta_currency_indicator, delta_currency in (
                ('_currency', currency),
                ('', company.currency_id),
            ):
                current_total_tax_amount = values[f'tax_amount{delta_currency_indicator}']
                if not current_total_tax_amount:
                    continue

                target_total_tax_amount = total_per_tax_line_key[tax_line_key][f'tax_amount{delta_currency_indicator}']
                delta_total_tax_amount = target_total_tax_amount - current_total_tax_amount

                target_factors = [
                    {
                        'factor': tax_data[f'tax_amount{delta_currency_indicator}'],
                        'tax_data': tax_data,
                    }
                    for _base_line, taxes_data in values['base_line_x_taxes_data']
                    for tax_data in taxes_data
                ]
                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=delta_currency.decimal_places,
                    delta_amount=delta_total_tax_amount,
                    target_factors=target_factors,
                )
                for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                    tax_data = target_factor['tax_data']
                    tax_data[f'tax_amount{delta_currency_indicator}'] += amount_to_distribute

    @api.model
    def _round_base_lines_tax_details(self, base_lines, company, tax_lines=None):
        """ Round the 'tax_details' added to base_lines.

        This method copies all float prefixed with 'raw_' to the corresponding float without 'raw_'.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:  A list of base lines.
        :param company:     The company owning the base lines.
        :param tax_lines:   An optional list of tax lines (for manual tax amounts).
        """
        # Raw rounding.
        for base_line in base_lines:
            tax_details = base_line['tax_details']

            for suffix, currency in (('_currency', base_line['currency_id']), ('', company.currency_id)):
                total_excluded_field = f'total_excluded{suffix}'
                tax_details[total_excluded_field] = currency.round(tax_details[f'raw_{total_excluded_field}'])

                for tax_data in tax_details['taxes_data']:
                    for prefix in ('base', 'tax'):
                        field = f'{prefix}_amount{suffix}'
                        tax_data[field] = currency.round(tax_data[f'raw_{field}'])

        # Apply 'manual_tax_amounts'.
        for base_line in base_lines:
            manual_tax_amounts = base_line['manual_tax_amounts']
            rate = base_line['rate']
            tax_details = base_line['tax_details']

            for suffix, currency in (('_currency', base_line['currency_id']), ('', company.currency_id)):
                total_field = f'total_excluded{suffix}'
                manual_field = f'manual_{total_field}'
                if base_line[manual_field] is not None:
                    tax_details[total_field] = base_line[manual_field]
                    if suffix == '_currency' and rate:
                        tax_details['total_excluded'] = company.currency_id.round(tax_details[total_field] / rate)

                for tax_data in tax_details['taxes_data']:
                    tax = tax_data['tax']
                    reverse_charge_sign = -1 if tax_data['is_reverse_charge'] else 1
                    current_manual_tax_amounts = manual_tax_amounts and manual_tax_amounts.get(str(tax.id)) or {}
                    for prefix, factor in (('base', 1), ('tax', reverse_charge_sign)):
                        field = f'{prefix}_amount{suffix}'
                        if field in current_manual_tax_amounts:
                            tax_data[field] = currency.round(factor * current_manual_tax_amounts[field])
                            if suffix == '_currency' and rate:
                                tax_data[f'{prefix}_amount'] = company.currency_id.round(tax_data[field] / rate)

        # Compute 'total_included' & add 'delta_total_excluded'.
        for base_line in base_lines:
            tax_details = base_line['tax_details']

            for suffix in ('_currency', ''):
                tax_details[f'delta_total_excluded{suffix}'] = 0.0
                tax_details[f'total_included{suffix}'] = tax_details[f'total_excluded{suffix}']

                for tax_data in tax_details['taxes_data']:
                    tax_details[f'total_included{suffix}'] += tax_data[f'tax_amount{suffix}']

        self._round_tax_details_tax_amounts(base_lines, company)
        self._round_tax_details_base_lines(base_lines, company)
        self._round_tax_details_tax_amounts_from_tax_lines(base_lines, company, tax_lines)

    # ─────────────────────────────────────────────────────────────────
    # AGGREGATOR OF TAX DETAILS
    # ─────────────────────────────────────────────────────────────────

    @api.model
    def _aggregate_base_line_tax_details(self, base_line, grouping_function):
        """ Aggregate the tax details for a single line according a custom grouping function.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_line:           A base line generated by '_prepare_base_line_for_taxes_computation'.
        :param grouping_function:   A function taking <base_line, tax_data> returning a grouping key.
        :return: A mapping <grouping_key, amounts>.
        """
        values_per_grouping_key = {}
        tax_details = base_line['tax_details']
        taxes_data = tax_details['taxes_data']
        manual_tax_amounts = base_line['manual_tax_amounts']

        # If there are no taxes, we pass None to the grouping function.
        for tax_data in (taxes_data or [None]):
            current_manual_tax_amounts = manual_tax_amounts and tax_data and manual_tax_amounts.get(str(tax_data['tax'].id)) or {}

            grouping_key = grouping_function(base_line, tax_data)
            if isinstance(grouping_key, dict):
                grouping_key = frozendict(grouping_key)

            # Base amount.
            if grouping_key not in values_per_grouping_key:
                values = values_per_grouping_key[grouping_key] = {
                    'grouping_key': grouping_key,
                    'taxes_data': [],
                }
                for suffix in ('_currency', ''):
                    excluded_rounded_field = f'total_excluded{suffix}'
                    excluded_delta_field = f'delta_{excluded_rounded_field}'
                    excluded_raw_field = f'raw_{excluded_rounded_field}'
                    excluded_target_field = f'target_{excluded_rounded_field}'
                    excluded_manual_field = f'manual_{excluded_rounded_field}'
                    excluded_rounded_amount = tax_details[excluded_rounded_field] + tax_details[excluded_delta_field]
                    excluded_raw_amount = tax_details[excluded_raw_field]
                    values[excluded_rounded_field] = excluded_rounded_amount
                    values[excluded_raw_field] = excluded_raw_amount
                    if base_line[excluded_manual_field] is not None:
                        excluded_target_amount = base_line[excluded_manual_field]
                    elif not suffix and base_line['manual_total_excluded_currency'] is not None:
                        excluded_target_amount = excluded_rounded_amount
                    else:
                        excluded_target_amount = excluded_raw_amount
                    values[excluded_target_field] = excluded_target_amount

                    tax_base_rounded_field = f'base_amount{suffix}'
                    tax_base_raw_field = f'raw_{tax_base_rounded_field}'
                    tax_base_target_field = f'target_{tax_base_rounded_field}'
                    if tax_data:
                        values[tax_base_rounded_field] = tax_data[tax_base_rounded_field]
                        values[tax_base_raw_field] = tax_data[tax_base_raw_field]
                        if tax_base_rounded_field in current_manual_tax_amounts:
                            values[tax_base_target_field] = current_manual_tax_amounts[tax_base_rounded_field]
                        elif not suffix and 'base_amount_currency' in current_manual_tax_amounts:
                            values[tax_base_target_field] = tax_data[tax_base_rounded_field]
                        else:
                            values[tax_base_target_field] = tax_data[tax_base_raw_field]
                    else:
                        values[tax_base_rounded_field] = excluded_rounded_amount
                        values[tax_base_raw_field] = excluded_raw_amount
                        values[tax_base_target_field] = excluded_target_amount

                    tax_rounded_field = f'tax_amount{suffix}'
                    tax_raw_field = f'raw_{tax_rounded_field}'
                    tax_target_field = f'target_{tax_rounded_field}'
                    values[tax_rounded_field] = 0.0
                    values[tax_raw_field] = 0.0
                    values[tax_target_field] = 0.0

            # Tax amount.
            if tax_data:
                reverse_charge_sign = -1 if tax_data['is_reverse_charge'] else 1
                values = values_per_grouping_key[grouping_key]
                for suffix in ('_currency', ''):
                    tax_rounded_field = f'tax_amount{suffix}'
                    tax_raw_field = f'raw_{tax_rounded_field}'
                    tax_target_field = f'target_{tax_rounded_field}'
                    values[tax_rounded_field] += tax_data[tax_rounded_field]
                    values[tax_raw_field] += tax_data[tax_raw_field]
                    if tax_rounded_field in current_manual_tax_amounts:
                        values[tax_target_field] += reverse_charge_sign * current_manual_tax_amounts[tax_rounded_field]
                    elif not suffix and 'tax_amount_currency' in current_manual_tax_amounts:
                        values[tax_target_field] = tax_data[tax_rounded_field]
                    else:
                        values[tax_target_field] += tax_data[tax_raw_field]
                values['taxes_data'].append(tax_data)

        return values_per_grouping_key

    @api.model
    def _aggregate_base_lines_tax_details(self, base_lines, grouping_function):
        """ Shortcut to call '_aggregate_base_line_tax_details' on multiple base lines.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          A list of base lines.
        :param grouping_function:   See '_aggregate_base_line_tax_details'.
        :return: A list of tuple <base_line, results>.
        """
        return [
            (base_line, self._aggregate_base_line_tax_details(base_line, grouping_function))
            for base_line in base_lines
        ]

    @api.model
    def _aggregate_base_lines_aggregated_values(self, base_lines_aggregated_values):
        """ Aggregate the values returned by '_aggregate_base_lines_tax_details' for the whole document.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines_aggregated_values: The result of '_aggregate_base_lines_tax_details'.
        :return: A mapping <grouping_key, amounts>.
        """
        default_float_fields = set()
        for prefix in ('', 'raw_', 'target_'):
            for suffix in ('_currency', ''):
                for field in ('base_amount', 'tax_amount', 'total_excluded'):
                    default_float_fields.add(f'{prefix}{field}{suffix}')

        values_per_grouping_key = defaultdict(lambda: {
            **dict.fromkeys(default_float_fields, 0.0),
            'base_line_x_taxes_data': [],
        })
        for base_line, aggregated_values in base_lines_aggregated_values:
            for grouping_key, values in aggregated_values.items():
                agg_values = values_per_grouping_key[grouping_key]
                for field in default_float_fields:
                    agg_values[field] += values[field]
                agg_values['grouping_key'] = grouping_key
                agg_values['base_line_x_taxes_data'].append((base_line, values['taxes_data']))
        return values_per_grouping_key

    # ─────────────────────────────────────────────────────────────────
    # TAX TOTALS SUMMARY
    # ─────────────────────────────────────────────────────────────────

    @api.model
    def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
        """ Compute the tax totals details for the business documents.

        Don't forget to call '_add_tax_details_in_base_lines' and
        '_round_base_lines_tax_details' before calling this method.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:      A list of base lines.
        :param currency:        The currency of the base lines.
        :param company:         The company owning the base lines.
        :param cash_rounding:   An optional cash rounding object.
        :return: A dictionary with tax totals.
        """
        tax_totals_summary = {
            'currency_id': currency.id,
            'currency_pd': currency.rounding,
            'company_currency_id': company.currency_id.id,
            'company_currency_pd': company.currency_id.rounding,
            'has_tax_groups': False,
            'subtotals': [],
            'base_amount_currency': 0.0,
            'base_amount': 0.0,
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
        }

        # Global tax values.
        def global_grouping_function(base_line, tax_data):
            return True if tax_data else None

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, global_grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            if grouping_key:
                tax_totals_summary['has_tax_groups'] = True
            tax_totals_summary['base_amount_currency'] += values['total_excluded_currency']
            tax_totals_summary['base_amount'] += values['total_excluded']
            tax_totals_summary['tax_amount_currency'] += values['tax_amount_currency']
            tax_totals_summary['tax_amount'] += values['tax_amount']

        # Tax groups.
        untaxed_amount_subtotal_label = _("Untaxed Amount")
        subtotals = defaultdict(lambda: {
            'tax_groups': [],
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
            'base_amount_currency': 0.0,
            'base_amount': 0.0,
        })

        def tax_group_grouping_function(base_line, tax_data):
            return tax_data['tax'].tax_group_id if tax_data else None

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, tax_group_grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        sorted_total_per_tax_group = sorted(
            [values for grouping_key, values in values_per_grouping_key.items() if grouping_key],
            key=lambda values: (values['grouping_key'].sequence, values['grouping_key'].id),
        )

        encountered_base_amounts = set()
        subtotals_order = {}
        for order, values in enumerate(sorted_total_per_tax_group):
            tax_group = values['grouping_key']

            # Get all involved taxes in the tax group.
            involved_taxes = self.env['account.tax']
            for _base_line, taxes_data in values['base_line_x_taxes_data']:
                for tax_data in taxes_data:
                    involved_taxes |= tax_data['tax']

            # Compute the display base amounts.
            if set(involved_taxes.mapped('amount_type')) == {'fixed'}:
                display_base_amount = False
                display_base_amount_currency = False
            elif set(involved_taxes.mapped('amount_type')) == {'division'} and all(involved_taxes.mapped('price_include')):
                display_base_amount = 0.0
                display_base_amount_currency = 0.0
                for base_line, _taxes_data in values['base_line_x_taxes_data']:
                    tax_details = base_line['tax_details']
                    display_base_amount += (
                        tax_details['total_excluded']
                        + tax_details['delta_total_excluded']
                    )
                    display_base_amount_currency += (
                        tax_details['total_excluded_currency']
                        + tax_details['delta_total_excluded_currency']
                    )
                    for tax_data in tax_details['taxes_data']:
                        if tax_data['tax'].amount_type == 'division':
                            display_base_amount_currency += tax_data['tax_amount_currency']
                            display_base_amount += tax_data['tax_amount']
            else:
                display_base_amount = values['base_amount']
                display_base_amount_currency = values['base_amount_currency']

            if display_base_amount_currency is not False:
                encountered_base_amounts.add(float_repr(display_base_amount_currency, currency.decimal_places))

            # Order of the subtotals.
            preceding_subtotal = tax_group.preceding_subtotal or untaxed_amount_subtotal_label
            if preceding_subtotal not in subtotals_order:
                subtotals_order[preceding_subtotal] = order

            subtotals[preceding_subtotal]['tax_groups'].append({
                'id': tax_group.id,
                'involved_tax_ids': involved_taxes.ids,
                'tax_amount_currency': values['tax_amount_currency'],
                'tax_amount': values['tax_amount'],
                'base_amount_currency': values['base_amount_currency'],
                'base_amount': values['base_amount'],
                'display_base_amount_currency': display_base_amount_currency,
                'display_base_amount': display_base_amount,
                'group_name': tax_group.name,
                'group_label': tax_group.pos_receipt_label,
            })

        # Subtotals.
        if not subtotals:
            subtotals[untaxed_amount_subtotal_label]

        ordered_subtotals = sorted(subtotals.items(), key=lambda item: subtotals_order.get(item[0], 0))
        accumulated_tax_amount_currency = 0.0
        accumulated_tax_amount = 0.0
        for subtotal_label, subtotal in ordered_subtotals:
            subtotal['name'] = subtotal_label
            subtotal['base_amount_currency'] = tax_totals_summary['base_amount_currency'] + accumulated_tax_amount_currency
            subtotal['base_amount'] = tax_totals_summary['base_amount'] + accumulated_tax_amount
            for tax_group in subtotal['tax_groups']:
                subtotal['tax_amount_currency'] += tax_group['tax_amount_currency']
                subtotal['tax_amount'] += tax_group['tax_amount']
                accumulated_tax_amount_currency += tax_group['tax_amount_currency']
                accumulated_tax_amount += tax_group['tax_amount']
            tax_totals_summary['subtotals'].append(subtotal)

        # Cash rounding
        cash_rounding_lines = [base_line for base_line in base_lines if base_line['special_type'] == 'cash_rounding']
        if cash_rounding_lines:
            tax_totals_summary['cash_rounding_base_amount_currency'] = 0.0
            tax_totals_summary['cash_rounding_base_amount'] = 0.0
            for base_line in cash_rounding_lines:
                tax_details = base_line['tax_details']
                tax_totals_summary['cash_rounding_base_amount_currency'] += tax_details['total_excluded_currency']
                tax_totals_summary['cash_rounding_base_amount'] += tax_details['total_excluded']
        elif cash_rounding:
            strategy = cash_rounding.strategy
            cash_rounding_pd = cash_rounding.rounding
            cash_rounding_method = cash_rounding.rounding_method
            total_amount_currency = tax_totals_summary['base_amount_currency'] + tax_totals_summary['tax_amount_currency']
            total_amount = tax_totals_summary['base_amount'] + tax_totals_summary['tax_amount']
            expected_total_amount_currency = float_round(
                total_amount_currency,
                precision_rounding=cash_rounding_pd,
                rounding_method=cash_rounding_method,
            )
            cash_rounding_base_amount_currency = expected_total_amount_currency - total_amount_currency
            rate = abs(total_amount_currency / total_amount) if total_amount else 0.0
            cash_rounding_base_amount = company.currency_id.round(cash_rounding_base_amount_currency / rate) if rate else 0.0
            if not currency.is_zero(cash_rounding_base_amount_currency):
                if strategy == 'add_invoice_line':
                    tax_totals_summary['cash_rounding_base_amount_currency'] = cash_rounding_base_amount_currency
                    tax_totals_summary['cash_rounding_base_amount'] = cash_rounding_base_amount
                    tax_totals_summary['base_amount_currency'] += cash_rounding_base_amount_currency
                    tax_totals_summary['base_amount'] += cash_rounding_base_amount
                    subtotals[untaxed_amount_subtotal_label]['base_amount_currency'] += cash_rounding_base_amount_currency
                    subtotals[untaxed_amount_subtotal_label]['base_amount'] += cash_rounding_base_amount
                elif strategy == 'biggest_tax':
                    all_subtotal_tax_group = [
                        (subtotal, tax_group)
                        for subtotal in tax_totals_summary['subtotals']
                        for tax_group in subtotal['tax_groups']
                    ]

                    if all_subtotal_tax_group:
                        max_subtotal, max_tax_group = max(
                            all_subtotal_tax_group,
                            key=lambda item: item[1]['tax_amount_currency'],
                        )
                        max_tax_group['tax_amount_currency'] += cash_rounding_base_amount_currency
                        max_tax_group['tax_amount'] += cash_rounding_base_amount
                        max_subtotal['tax_amount_currency'] += cash_rounding_base_amount_currency
                        max_subtotal['tax_amount'] += cash_rounding_base_amount
                        tax_totals_summary['tax_amount_currency'] += cash_rounding_base_amount_currency
                        tax_totals_summary['tax_amount'] += cash_rounding_base_amount
                    else:
                        cash_rounding_base_amount_currency = 0.0
                        cash_rounding_base_amount = 0.0

        # Subtract the cash rounding from the untaxed amounts.
        cash_rounding_base_amount_currency = tax_totals_summary.get('cash_rounding_base_amount_currency', 0.0)
        cash_rounding_base_amount = tax_totals_summary.get('cash_rounding_base_amount', 0.0)
        tax_totals_summary['base_amount_currency'] -= cash_rounding_base_amount_currency
        tax_totals_summary['base_amount'] -= cash_rounding_base_amount
        for subtotal in tax_totals_summary['subtotals']:
            subtotal['base_amount_currency'] -= cash_rounding_base_amount_currency
            subtotal['base_amount'] -= cash_rounding_base_amount
        encountered_base_amounts.add(float_repr(tax_totals_summary['base_amount_currency'], currency.decimal_places))
        tax_totals_summary['same_tax_base'] = len(encountered_base_amounts) == 1

        # Non deductible lines (not implemented in JS)
        taxed_non_deductible_lines = [
            base_line
            for base_line in base_lines
            if base_line['special_type'] == 'non_deductible'
            and base_line['tax_ids']
        ]
        if taxed_non_deductible_lines:
            base_lines_aggregated_values = self._aggregate_base_lines_tax_details(taxed_non_deductible_lines, tax_group_grouping_function)
            values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
            for subtotal in tax_totals_summary['subtotals']:
                for tax_group in subtotal['tax_groups']:
                    tax_values = values_per_grouping_key[self.env['account.tax.group'].browse(tax_group['id'])]
                    tax_group['non_deductible_tax_amount'] = tax_values['tax_amount']
                    tax_group['non_deductible_tax_amount_currency'] = tax_values['tax_amount_currency']

                    tax_group['tax_amount'] -= tax_values['tax_amount']
                    tax_group['tax_amount_currency'] -= tax_values['tax_amount_currency']
                    tax_group['base_amount'] -= tax_values['base_amount']
                    tax_group['base_amount_currency'] -= tax_values['base_amount_currency']

                    subtotal['tax_amount'] -= tax_values['tax_amount']
                    subtotal['tax_amount_currency'] -= tax_values['tax_amount_currency']

                    tax_totals_summary['tax_amount'] -= tax_values['tax_amount']
                    tax_totals_summary['tax_amount_currency'] -= tax_values['tax_amount_currency']

        # Total amount.
        tax_totals_summary['total_amount_currency'] = \
            tax_totals_summary['base_amount_currency'] + tax_totals_summary['tax_amount_currency'] + cash_rounding_base_amount_currency
        tax_totals_summary['total_amount'] = \
            tax_totals_summary['base_amount'] + tax_totals_summary['tax_amount'] + cash_rounding_base_amount

        return tax_totals_summary

    @api.model
    def _exclude_tax_groups_from_tax_totals_summary(self, tax_totals, ids_to_exclude):
        """ Post-process the tax totals and wrap some tax groups into the base amount.

        [!] Only added python-side.

        :param tax_totals:      The tax totals generated by '_get_tax_totals_summary'.
        :param ids_to_exclude:  The ids of the tax groups to exclude.
        :return:                A new tax totals without the excluded ids.
        """
        tax_totals = copy.deepcopy(tax_totals)
        ids_to_exclude = set(ids_to_exclude)

        subtotals = []
        for subtotal in tax_totals['subtotals']:
            tax_groups = []
            for tax_group in subtotal['tax_groups']:
                if tax_group['id'] in ids_to_exclude:
                    subtotal['base_amount_currency'] += tax_group['tax_amount_currency']
                    subtotal['base_amount'] += tax_group['tax_amount']
                    subtotal['tax_amount_currency'] -= tax_group['tax_amount_currency']
                    subtotal['tax_amount'] -= tax_group['tax_amount']
                    tax_totals['base_amount_currency'] += tax_group['tax_amount_currency']
                    tax_totals['base_amount'] += tax_group['tax_amount']
                    tax_totals['tax_amount_currency'] -= tax_group['tax_amount_currency']
                    tax_totals['tax_amount'] -= tax_group['tax_amount']
                else:
                    tax_groups.append(tax_group)

            if tax_groups:
                subtotal['tax_groups'] = tax_groups
                subtotals.append(subtotal)

        tax_totals['subtotals'] = subtotals
        return tax_totals

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────

    def flatten_taxes_hierarchy(self):
        return self._flatten_taxes_and_sort_them()[0]

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None,
                    is_refund=False, handle_price_include=True, rounding_method=None):
        """Compute tax amounts for the given price_unit and quantity.

        Simplified version without accounting data (accounts, tags).
        For the full version with accounting data, use the ``account`` module.

        :param price_unit: The unit price.
        :param currency: The currency (defaults to company currency).
        :param quantity: The quantity.
        :param product: The product.
        :param partner: The partner (used for lang).
        :param is_refund: Whether this is a refund.
        :param handle_price_include: If False, ignore price-included taxes.
        :param rounding_method: Override rounding method.
        :returns: A dict with 'total_excluded', 'total_included', 'taxes'.
        """
        if not self:
            company = self.env.company
        else:
            company = self[0].company_id._accessible_branches()[:1] or self[0].company_id

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
        )
        self._add_tax_details_in_base_line(base_line, company, rounding_method=rounding_method)

        tax_details = base_line['tax_details']
        total_excluded = tax_details['raw_total_excluded_currency']
        total_included = tax_details['raw_total_included_currency']

        taxes = []
        for tax_data in tax_details['taxes_data']:
            tax = tax_data['tax']
            taxes.append({
                'id': tax.id,
                'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
                'amount': tax_data['raw_tax_amount_currency'],
                'base': tax_data['raw_base_amount_currency'],
                'sequence': tax.sequence,
                'price_include': tax.price_include,
                'is_reverse_charge': tax_data['is_reverse_charge'],
                'group': tax_data['group'],
            })

        if self.env.context.get('round_base', True):
            total_excluded = currency.round(total_excluded)
            total_included = currency.round(total_included)

        return {
            'taxes': taxes,
            'total_excluded': total_excluded,
            'total_included': total_included,
        }

    def _filter_taxes_by_company(self, company_id):
        """ Filter taxes by the given company, walking up the company hierarchy."""
        if not self:
            return self
        taxes, company = self.env['account.tax'], company_id
        while not taxes and company:
            taxes = self.filtered(lambda t: t.company_id == company)
            company = company.sudo().parent_id
        return taxes

    @api.model
    def _fix_tax_included_price(self, price, prod_taxes, line_taxes):
        """Subtract tax amount from price when corresponding "price included" taxes do not apply."""
        prod_taxes = prod_taxes._origin
        line_taxes = line_taxes._origin
        incl_tax = prod_taxes.filtered(lambda tax: tax not in line_taxes and tax.price_include)
        if incl_tax:
            return incl_tax.compute_all(price)['total_excluded']
        return price

    @api.model
    def _fix_tax_included_price_company(self, price, prod_taxes, line_taxes, company_id):
        if company_id:
            prod_taxes = prod_taxes.filtered(lambda tax: tax.company_id == company_id)
            line_taxes = line_taxes.filtered(lambda tax: tax.company_id == company_id)
        return self._fix_tax_included_price(price, prod_taxes, line_taxes)

    def _get_description_plaintext(self):
        self.ensure_one()
        if is_html_empty(self.description):
            return ''
        return html2plaintext(self.description)


# ════════════════════════════════════════════════════════════════════════
# TAX REPARTITION LINE
# ════════════════════════════════════════════════════════════════════════

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
        help="Factor to apply on the account move lines generated from this distribution line, in percents",
    )
    factor = fields.Float(
        string="Factor Ratio",
        compute="_compute_factor",
        help="Factor to apply on the account move lines generated from this distribution line",
    )
    repartition_type = fields.Selection(
        string="Based On",
        selection=[('base', 'Base'), ('tax', 'of tax')],
        required=True,
        default='tax',
        help="Base on which the factor will be applied.",
    )
    document_type = fields.Selection(
        string="Related to",
        selection=[('invoice', 'Invoice'), ('refund', 'Refund')],
        required=True,
    )
    tax_id = fields.Many2one(
        comodel_name='account.tax',
        index='btree_not_null',
        ondelete='cascade',
        check_company=True,
    )
    company_id = fields.Many2one(
        string="Company",
        comodel_name='res.company',
        related="tax_id.company_id",
        store=True,
        help="The company this distribution line belongs to.",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=1,
        help=(
            "The order in which distribution lines are displayed and matched. "
            "For refunds to work properly, invoice distribution lines should be "
            "arranged in the same order as the credit note distribution lines "
            "they correspond to."
        ),
    )

    @api.depends('factor_percent')
    def _compute_factor(self):
        for record in self:
            record.factor = record.factor_percent / 100.0
