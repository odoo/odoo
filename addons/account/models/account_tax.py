from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import frozendict, groupby, html2plaintext, is_html_empty, split_every, SQL
from odoo.tools.float_utils import float_is_zero, float_repr, float_round, float_compare
from odoo.tools.misc import clean_context, formatLang
from odoo.tools.translate import html_translate

from collections import defaultdict
from collections.abc import Iterable
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
        string='Tax Payable Account',
        help="Tax current account used as a counterpart to the Tax Closing Entry when in favor of the authorities.")
    tax_receivable_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
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
    _rec_names_search = ['name', 'description', 'invoice_label']
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(string='Tax Name', required=True, translate=True, tracking=True)
    type_tax_use = fields.Selection(TYPE_TAX_USE, string='Tax Type', required=True, default="sale", tracking=True,
        help="Determines where the tax is selectable. Note: 'None' means a tax can't be used by itself, however it can still be used in a group. 'adjustment' is used to perform tax adjustment.")
    tax_scope = fields.Selection([('service', 'Services'), ('consu', 'Goods')], string="Tax Scope", help="Restrict the use of taxes to a type of product.")
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
    is_used = fields.Boolean(string="Tax used", compute='_compute_is_used')
    repartition_lines_str = fields.Char(string="Repartition Lines", tracking=True, compute='_compute_repartition_lines_str')
    invoice_legal_notes = fields.Html(string="Legal Notes", translate=True, help="Legal mentions that have to be printed on the invoices.")
    # Technical field depicting if the tax has at least one repartition line with a percentage below 0.
    # Used for the taxes computation to manage the reverse charge taxes having a repartition +100 -100.
    has_negative_factor = fields.Boolean(compute='_compute_has_negative_factor')

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

    @api.constrains('tax_exigibility', 'cash_basis_transition_account_id')
    def _constrains_cash_basis_transition_account(self):
        for record in self:
            if (
                record.tax_exigibility == 'on_payment'
                and not record.cash_basis_transition_account_id.reconcile
                and not self.env.context.get('chart_template_load')
            ):
                raise ValidationError(_("The cash basis transition account needs to allow reconciliation."))

    @api.model
    @api.readonly
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        domain = Domain(domain or Domain.TRUE)
        if 'search_default_domestictax' in self.env.context:
            domain &= Domain('fiscal_position_ids', '=', False) | Domain('fiscal_position_ids.is_domestic', '=', True)
        if fp_id := self.env.context.get('dynamic_fiscal_position_id'):
            domain &= Domain('fiscal_position_ids', 'in', [False, int(fp_id)])
        if self.env.context.get('hide_original_tax_ids') and fp_id:
            domain &= Domain('replacing_tax_ids', 'not any', domain)
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

    def _hook_compute_is_used(self, tax_to_compute):
        '''
            Override to compute the ids of taxes used in other modules. It takes
            as parameter a set of tax ids. It should return a set containing the
            ids of the taxes from that input set that are used in transactions.
        '''
        return set()

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

    def _compute_is_used(self):
        used_taxes = set()

        if self.ids:
            # Fetch for taxes used in account moves
            self.env['account.move.line'].flush_model(['tax_ids'])
            used_taxes.update(id_ for [id_] in self.env.execute_query(SQL(
                """ SELECT id
                    FROM account_tax
                    WHERE EXISTS(
                        SELECT 1
                        FROM account_move_line_account_tax_rel AS line
                        WHERE account_tax_id IN %s
                        AND account_tax.id = line.account_tax_id
                    ) """,
                tuple(self.ids),
            )))
            taxes_to_compute = set(self.ids) - used_taxes

            # Fetch for taxes used in reconciliation
            if taxes_to_compute:
                self.env['account.reconcile.model.line'].flush_model(['tax_ids'])
                used_taxes.update(id_ for [id_] in self.env.execute_query(SQL(
                    """ SELECT id
                        FROM account_tax
                        WHERE EXISTS(
                            SELECT 1
                            FROM account_reconcile_model_line_account_tax_rel AS reco
                            WHERE account_tax_id IN %s
                            AND account_tax.id = reco.account_tax_id
                        ) """,
                    tuple(taxes_to_compute)
                )))
                taxes_to_compute -= used_taxes

            # Fetch for tax used in other modules
            if taxes_to_compute:
                used_taxes.update(self._hook_compute_is_used(taxes_to_compute))

        for tax in self:
            tax.is_used = tax._origin.id in used_taxes

    @api.depends('repartition_line_ids.account_id', 'repartition_line_ids.sequence', 'repartition_line_ids.factor_percent', 'repartition_line_ids.use_in_tax_closing', 'repartition_line_ids.tag_ids')
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
                body = Markup("<b>{type}</b> {rep} {seq}:<ul class='mb-0 ps-4'>{changes}</ul>").format(
                    type=document_type.capitalize(),
                    rep=_('repartition line'),
                    seq=sequence,
                    changes=Markup().join(
                        [Markup("""
                            <li>
                                <span class='o-mail-Message-trackingOld me-1 px-1 text-muted fw-bold'>{old}</span>
                                <i class='o-mail-Message-trackingSeparator fa fa-long-arrow-right mx-1 text-600'/>
                                <span class='o-mail-Message-trackingNew me-1 fw-bold text-info'>{new}</span>
                                <span class='o-mail-Message-trackingField ms-1 fst-italic text-muted'>({diff})</span>
                            </li>
                        """).format(old=old_value[diff_key], new=new_value[diff_key], diff=diff_key)
                        for diff_key in diff_keys]
                    )
                )
                super()._message_log(body=body)

        for (document_type, sequence), operation, value in added_and_deleted_lines:
            body = Markup("<b>{op} {type}</b> {rep} {seq}:<ul class='mb-0 ps-4'>{changes}</ul>").format(
                op=operation,
                type=document_type.capitalize(),
                rep=_('repartition line'),
                seq=sequence,
                changes=Markup().join(
                    [Markup("""
                        <li>
                            <span class='o-mail-Message-trackingNew me-1 fw-bold text-info'>{value}</span>
                            <span class='o-mail-Message-trackingField ms-1 fst-italic text-muted'>({diff})</span>
                        </li>
                    """).format(value=value[key], diff=key)
                    for key in value]
                )
            )
            super()._message_log(body=body)
        return

    def _message_log(self, **kwargs):
        # OVERRIDE _message_log
        # We only log the modification of the tracked fields if the tax is
        # currently used in transactions. We remove the `repartition_lines_str`
        # from tracked value to avoid having it logged twice (once in the raw
        # string format and one in the nice formatted way thanks to
        # `_message_log_repartition_lines`)

        self.ensure_one()

        if self.is_used:
            repartition_line_str_field_id = self.env['ir.model.fields']._get('account.tax', 'repartition_lines_str').id
            for tracked_value_id in kwargs['tracking_value_ids']:
                if tracked_value_id[2]['field_id'] == repartition_line_str_field_id:
                    kwargs['tracking_value_ids'].remove(tracked_value_id)
                    self._message_log_repartition_lines(tracked_value_id[2]['old_value_char'], tracked_value_id[2]['new_value_char'])

            return super()._message_log(**kwargs)

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
        if sanitized.get('description') and not re.search(r'<[^>]+>', sanitized['description']):
            sanitized['description'] = f"<div>{sanitized['description']}</div>"

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
        context = clean_context(self.env.context)
        context.update({
            'mail_create_nosubscribe': True, # At create or message_post, do not subscribe the current user to the record thread
            'mail_auto_subscribe_no_notify': True, # Do no notify users set as followers of the mail thread
            'mail_create_nolog': True, # At create, do not log the automatic ‘<Document> created’ message
        })
        taxes = super(AccountTax, self.with_context(context)).create([self._sanitize_vals(vals) for vals in vals_list])
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

    @api.onchange('amount')
    def onchange_amount(self):
        if self.amount_type in ('percent', 'division') and self.amount != 0.0 and not self.invoice_label:
            self.invoice_label = "{0:.4g}%".format(self.amount)

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

    # -------------------------------------------------------------------------
    # HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js / account_tax.py)

    # TAXES COMPUTATION
    # -------------------------------------------------------------------------

    def _eval_taxes_computation_prepare_product_fields(self):
        """ Get the fields to create the evaluation context from the product for the taxes computation.

        This method is not there in the javascript code.
        Anybody wanted to use the product during the taxes computation js-side needs to preload the product fields
        using this method.

        [!] Only added python-side.

        :return: A set of fields to be extracted from the product to evaluate the taxes computation.
        """
        return set()

    @api.model
    def _eval_taxes_computation_prepare_product_default_values(self, field_names):
        """ Prepare the default values for the product according the fields passed as parameter.
        The dictionary contains the default values to be considered if there is no product at all.

        This method is not there in the javascript code.
        Anybody wanted to use the product during the taxes computation js-side needs to preload the default product fields
        using this method.

        [!] Only added python-side.

        :param field_names: A set of fields returned by '_eval_taxes_computation_get_product_fields'.
        :return: A mapping <field_name> => <field_info> where field_info is a dict containing:
            * type: the type of the field.
            * default_value: the default value in case there is no product.
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
        """ Convert the product passed as parameter to a dictionary to be passed to '_eval_taxes_computation_prepare_context'.

        Note: In javascript, this method is not available. You have to ensure the necessary product fields are well
        loaded to not break the management of taxes with custom formula byt using
        '_eval_taxes_computation_prepare_product_fields'.

        [!] Only added python-side.

        :param default_product_values:  The default product values generated by '_eval_taxes_computation_prepare_product_default_values'.
        :param product:                 An optional product.product record.
        :return:                        The values representing the product.
        """
        product = product and product.sudo()  # tax computation may depend on restricted fields
        product_values = {}
        for field_name, field_info in default_product_values.items():
            product_values[field_name] = product and product[field_name] or field_info['default_value']
        return product_values

    def _eval_taxes_computation_turn_to_product_values(self, product=None):
        """ Helper purely in Python to call:
            '_eval_taxes_computation_prepare_product_fields'
            '_eval_taxes_computation_prepare_product_default_values'
            '_eval_taxes_computation_prepare_product_values'
        all at once.

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
        """ Get the fields to create the evaluation context from the product uom for the taxes computation.

        This method is not there in the javascript code.
        Anybody wanted to use the product during the taxes computation js-side needs to preload the product uom fields
        using this method.

        [!] Only added python-side.

        :return: A set of fields to be extracted from the product to evaluate the taxes computation.
        """
        return set()

    @api.model
    def _eval_taxes_computation_prepare_product_uom_default_values(self, field_names):
        """ Prepare the default values for the product uom according the fields passed as parameter.
        The dictionary contains the default values to be considered if there is no product uom at all.

        This method is not there in the javascript code.
        Anybody wanted to use the product uom during the taxes computation js-side needs to preload the default
        product uom fields using this method.

        [!] Only added python-side.

        :param field_names: A set of fields returned by '_eval_taxes_computation_get_product_uom_fields'.
        :return: A mapping <field_name> => <field_info> where field_info is a dict containing:
            * type: the type of the field.
            * default_value: the default value in case there is no product.
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
        """ Convert the product uom passed as parameter to a dictionary to be passed to '_eval_taxes_computation_prepare_context'.

        Note: In javascript, this method takes an additional parameter being the results of the
        '_eval_taxes_computation_prepare_product_uom_default_values' method because this method is not callable in javascript but must
        be passed to the client instead.

        [!] Only added python-side.

        :param default_product_uom_values:  The default product values generated by '_eval_taxes_computation_prepare_product_uom_default_values'.
        :param product_uom:                 An optional product.uom record.
        :return:                            The values representing the product uom.
        """
        product_uom = product_uom and product_uom.sudo()  # tax computation may depend on restricted fields
        product_uom_values = {}
        for field_name, field_info in default_product_uom_values.items():
            product_uom_values[field_name] = product_uom and product_uom[field_name] or field_info['default_value']
        return product_uom_values

    def _eval_taxes_computation_turn_to_product_uom_values(self, product_uom=None):
        """ Helper purely in Python to call:
            '_eval_taxes_computation_prepare_product_uom_fields'
            '_eval_taxes_computation_prepare_product_uom_default_values'
            '_eval_taxes_computation_prepare_product_uom_values'
        all at once.

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

    def _flatten_taxes_and_sort_them(self):
        """ Flattens the taxes contained in this recordset, returning all the
        children at the bottom of the hierarchy, in a recordset, ordered by sequence.
          Eg. considering letters as taxes and alphabetic order as sequence :
          [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :return: A tuple <sorted_taxes, group_per_tax> where:
            - sorted_taxes is a recordset of taxes.
            - group_per_tax maps each tax to its parent group of taxes if exists.
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

        :param special_mode:        The special mode of the taxes computation: False, 'total_excluded' or 'total_included'.
        :param filter_tax_function: Optional function to filter out some taxes from the computation.
        :return: A dictionary containing:
            * batch_per_tax: A mapping of each tax to its batch.
            * group_per_tax: A mapping of each tax retrieved from a group of taxes.
            * sorted_taxes: A recordset of all taxes in the order on which they need to be evaluated.
                            Note that we consider the sequence of the parent for group of taxes.
                            Eg. considering letters as taxes and alphabetic order as sequence :
                            [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]
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

    def _propagate_extra_taxes_base(self, tax, taxes_data, special_mode=False):
        """ In some cases, depending the computation order of taxes, the special_mode or the configuration
        of taxes (price included, affect base of subsequent taxes, etc), some taxes need to affect the base and
        the tax amount of the others. That's the purpose of this method: adding which tax need to be added as
        an 'extra_base' to the others.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param tax:             The tax for which we need to propagate the tax.
        :param taxes_data:      The computed values for taxes so far.
        :param special_mode:    The special mode of the taxes computation: False, 'total_excluded' or 'total_included'.
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

            # Suppose:
            # 1.
            # t1: price-excluded fixed tax of 1, include_base_amount
            # t2: price-included 10% tax
            # On a price unit of 120, t1 is computed first since the tax amount affects the price unit.
            # Then, t2 can be computed on 120 + 1 = 121.
            # However, since t1 is not price-included, its base amount is computed by removing first the tax amount of t2.
            # 2.
            # t1: price-included fixed tax of 1
            # t2: price-included 10% tax
            # On a price unit of 122, base amount of t2 is computed as 122 - 1 = 121
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

            # Suppose:
            # 1.
            # t1: price-included 10% tax
            # t2: price-excluded 10% tax
            # If the price unit is 121, the base amount of t1 is computed as 121 / 1.1 = 110
            # With special_mode = 'total_excluded', 110 is provided as price unit.
            # To compute the base amount of t2, we need to add back the tax amount of t1.
            # 2.
            # t1: price-included fixed tax of 1, include_base_amount
            # t2: price-included 10% tax
            # On a price unit of 121, with t1 being include_base_amount, the base amount of t2 is 121
            # With special_mode = 'total_excluded' 109 is provided as price unit.
            # To compute the base amount of t2, we need to add the tax amount of t1 first
            else:  # special_mode == 'total_excluded'
                if tax.include_base_amount:
                    for other_tax in get_tax_after():
                        if other_tax.is_base_affected:
                            add_extra_base(other_tax, 1)

        elif not tax.price_include:

            # Case of a tax affecting the base of the subsequent ones, no price included taxes.
            if special_mode in (False, 'total_excluded'):
                if tax.include_base_amount:
                    for other_tax in get_tax_after():
                        if other_tax.is_base_affected:
                            add_extra_base(other_tax, 1)

            # Suppose:
            # 1.
            # t1: price-excluded 10% tax, include base amount
            # t2: price-excluded 10% tax
            # On a price unit of 100,
            # The tax of t1 is 100 * 1.1 = 110.
            # The tax of t2 is 110 * 1.1 = 121.
            # With special_mode = 'total_included', 121 is provided as price unit.
            # The tax amount of t2 is computed like a price-included tax: 121 / 1.1 = 110.
            # Since t1 is 'include base amount', t2 has already been subtracted from the price unit.
            # 2.
            # t1: price-excluded fixed tax of 1
            # t2: price-excluded 10% tax
            # On a price unit of 110, the tax of t2 is 110 * 1.1 = 121
            # With special_mode = 'total_included', 122 is provided as price unit.
            # The base amount of t2 should be computed by removing the tax amount of t1 first
            else:  # special_mode == 'total_included'
                if not tax.include_base_amount:
                    for other_tax in get_tax_after():
                        add_extra_base(other_tax, -1)
                for other_tax in get_tax_before():
                    add_extra_base(other_tax, -1)

    def _eval_tax_amount_fixed_amount(self, batch, raw_base, evaluation_context):
        """ Eval the tax amount for a single tax during the first ascending order for fixed taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param batch:               The batch of taxes containing this tax.
        :param raw_base:            The base on which the tax should be computed.
        :param evaluation_context:  The context containing all relevant info to compute the tax.
        :return:                    The tax amount or None if it has be evaluated later.
        """
        if self.amount_type == 'fixed':
            sign = -1 if evaluation_context['price_unit'] < 0.0 else 1
            return sign * evaluation_context['quantity'] * self.amount

    def _eval_tax_amount_price_included(self, batch, raw_base, evaluation_context):
        """ Eval the tax amount for a single tax during the descending order for price-included taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param batch:               The batch of taxes containing this tax.
        :param raw_base:            The base on which the tax should be computed.
        :param evaluation_context:  The context containing all relevant info to compute the tax.
        :return:                    The tax amount.
        """
        self.ensure_one()
        if self.amount_type == 'percent':
            total_percentage = sum(tax.amount for tax in batch) / 100.0
            to_price_excluded_factor = 1 / (1 + total_percentage) if total_percentage != -1 else 0.0
            return raw_base * to_price_excluded_factor * self.amount / 100.0

        if self.amount_type == 'division':
            return raw_base * self.amount / 100.0

    def _eval_tax_amount_price_excluded(self, batch, raw_base, evaluation_context):
        """ Eval the tax amount for a single tax during the second ascending order for price-excluded taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param batch:               The batch of taxes containing this tax.
        :param raw_base:            The base on which the tax should be computed.
        :param evaluation_context:  The context containing all relevant info to compute the tax.
        :return:                    The tax amount.
        """
        self.ensure_one()
        if self.amount_type == 'percent':
            return raw_base * self.amount / 100.0

        if self.amount_type == 'division':
            total_percentage = sum(tax.amount for tax in batch) / 100.0
            incl_base_multiplicator = 1.0 if total_percentage == 1.0 else 1 - total_percentage
            return raw_base * self.amount / 100.0 / incl_base_multiplicator

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
        :param precision_rounding:  The rounding precision for the 'round_per_line' method.
        :param rounding_method:     'round_per_line' or 'round_globally'.
        :param product:             The product of the line.
        :param product_uom:         The product uom of the line.
        :param special_mode:        Indicate a special mode for the taxes computation.
                            * total_excluded: The initial base of computation excludes all price-included taxes.
                            Suppose a tax of 21% price included. Giving 100 with special_mode = 'total_excluded'
                            will give you the same as 121 without any special_mode.
                            * total_included: The initial base of computation is the total with taxes.
                            Suppose a tax of 21% price excluded. Giving 121 with special_mode = 'total_included'
                            will give you the same as 100 without any special_mode.
                            Note: You can only expect accurate symmetrical taxes computation with not rounded price_unit
                            as input and 'round_globally' computation. Otherwise, it's not guaranteed.
        :param manual_tax_amounts:  TO BE REMOVED IN MASTER.
        :param filter_tax_function: Optional function to filter out some taxes from the computation.
        :return: A dict containing:
            'evaluation_context':       The evaluation_context parameter.
            'taxes_data':               A list of dictionaries, one per tax containing:
                'tax':                      The tax record.
                'base':                     The base amount of this tax.
                'tax_amount':               The tax amount of this tax.
            'total_excluded':           The total without tax.
            'total_included':           The total with tax.
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

        # Define the order in which the taxes must be evaluated.
        # Fixed taxes are computed directly because they could affect the base of a price included batch right after.
        # Suppose:
        # t1: fixed tax of 1, include base amount
        # t2: 21% price included tax
        # If the price unit is 121, the base amount of t1 is computed as 121 / 1.1 = 110
        # With special_mode = 'total_excluded', 110 is provided as price unit.
        # To compute the base amount of t2, we need to add back the tax amount of t1.
        for tax in reversed(sorted_taxes):
            eval_tax_amount(tax._eval_tax_amount_fixed_amount, tax)

        # Then, let's travel the batches in the reverse order and process the price-included taxes.
        for tax in reversed(sorted_taxes):
            if taxes_data[tax.id]['price_include']:
                eval_tax_amount(tax._eval_tax_amount_price_included, tax)

        # Then, let's travel the batches in the normal order and process the price-excluded taxes.
        for tax in sorted_taxes:
            if not taxes_data[tax.id]['price_include']:
                eval_tax_amount(tax._eval_tax_amount_price_excluded, tax)

        # Mark the base to be computed in the descending order. The order doesn't matter for no special mode or 'total_excluded' but
        # it must be in the reverse order when special_mode is 'total_included'.
        subsequent_taxes = self.env['account.tax']
        for tax in reversed(sorted_taxes):
            tax_data = taxes_data[tax.id]
            if 'tax_amount' not in tax_data:
                continue

            # Base amount.
            tax_id_str = str(tax.id)
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

    # -------------------------------------------------------------------------
    # MAPPING PRICE_UNIT
    # -------------------------------------------------------------------------

    @api.model
    def _adapt_price_unit_to_another_taxes(self, price_unit, product, original_taxes, new_taxes, product_uom=None):
        """ From the price unit and taxes given as parameter, compute a new price unit corresponding to the
        new taxes.

        For example, from price_unit=106 and taxes=[6% tax-included], this method can compute a price_unit=121
        if new_taxes=[21% tax-included].

        The price_unit is only adapted when all taxes in 'original_taxes' are price-included even when
        'new_taxes' contains price-included taxes. This is made that way for the following example:

        Suppose a fiscal position B2C mapping 15% tax-excluded => 6% tax-included.
        If price_unit=100 with [15% tax-excluded], the price_unit is computed as 100 / 1.06 instead of becoming 106.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param price_unit:      The original price_unit.
        :param product:         The product.
        :param original_taxes:  A recordset of taxes from where you come from.
        :param new_taxes:       A recordset of the taxes you are mapping the price unit to.
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

    # -------------------------------------------------------------------------
    # GENERIC REPRESENTATION OF BUSINESS OBJECTS & METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _export_base_line_extra_tax_data(self, base_line):
        """ Export the extra values about the taxes engine into the extra_tax_data json field.

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
        """ Import the 'extra_tax_data' json value into the base line passed as parameter.
        For 'manual_tax_amounts', if the setup of the base line has been manually edited, we don't import the custom tax amounts from
        'extra_tax_data.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_line:       A base line generated by '_prepare_base_line_for_taxes_computation'.
        :param extra_tax_data:  The value stored in one of the 'extra_tax_data' field.
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
        :return: The base_lines that is no longer a refund lines.
        """
        return [self._turn_base_line_is_refund_flag_off(base_line) for base_line in base_lines]

    @api.model
    def _get_base_line_field_value_from_record(self, record, field, extra_values, fallback, from_base_line=False):
        """ Helper to extract a default value for a record or something looking like a record.

        Suppose field is 'product_id' and fallback is 'self.env['product.product']'

        if record is an account.move.line, the returned product_id will be `record.product_id._origin`.
        if record is a dict, the returned product_id will be `record.get('product_id', fallback)`.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param record:          A record or a dict or a falsy value.
        :param field:           The name of the field to extract.
        :param extra_values:    The extra kwargs passed in addition of 'record'.
        :param fallback:        The value to return if not found in record or extra_values.
        :param from_base_line:  Indicate if the value has to be retrieved automatically from the base_line and not the record.
                                False by default.
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
        """ Convert any representation of a business object ('record') into a base line being a python
        dictionary that will be used to use the generic helpers for the taxes computation.

        The whole method is designed to ease the conversion from a business record.
        For example, when passing either account.move.line, either sale.order.line or purchase.order.line,
        providing explicitely a 'product_id' in kwargs is not necessary since all those records already have
        an `product_id` field.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param record:  A representation of a business object a.k.a a record or a dictionary.
        :param kwargs:  The extra values to override some values that will be taken from the record.
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
            # - False for the normal behavior.
            # - total_included to force all taxes to be price included.
            # - total_excluded to force all taxes to be price excluded.
            'special_mode': kwargs.get('special_mode') or False,

            # A special typing of base line for some custom behavior:
            # - False for the normal behavior.
            # - early_payment if the base line represent an early payment in mixed mode.
            # - cash_rounding if the base line is a delta to round the business object for the cash rounding feature.
            # - non_deductible if the base line is used to compute non deductible amounts in bills.
            'special_type': kwargs.get('special_type') or False,

            # All computation are managing the foreign currency and the local one.
            # This is the rate to be applied when generating the tax details (see '_add_tax_details_in_base_line').
            'rate': load('rate', 1.0),

            # Add a function allowing to filter out some taxes during the evaluation. Those taxes can't be removed from the base_line
            # when dealing with group of taxes to maintain a correct link between the child tax and its parent.
            'filter_tax_function': kwargs.get('filter_tax_function') or None,

            # ===== Accounting stuff =====

            # The sign of the business object regarding its accounting balance.
            'sign': load('sign', 1.0),

            # If the document is a refund or not to know which repartition lines must be used.
            'is_refund': load('is_refund', False),

            # Extra fields for tax lines generation:
            'partner_id': load('partner_id', self.env['res.partner']),
            'account_id': load('account_id', self.env['account.account']),
            'analytic_distribution': load('analytic_distribution', None),
        }

        extra_tax_data = self._import_base_line_extra_tax_data(base_line, load('extra_tax_data', {}) or {})
        base_line.update({
            # Allow to split the computation of taxes on subset of lines. For example with a down payment of 300 on a sale order of 1000,
            # the last invoice will have an amount of 1000 - 300 = 700. However, the taxes should be computed in 2 subsets of lines:
            # - the original lines for a total of 1000.0
            # - the previous down payment lines for a total of -300.0
            'computation_key': kwargs.get('computation_key') or extra_tax_data.get('computation_key'),

            # For all computation that are inferring a base amount in order to reach a total you know in advance, you have to force some
            # base/tax amounts for the computation (E.g. down payment, combo products, global discounts etc).
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

    @api.model
    def _prepare_tax_line_for_taxes_computation(self, record, **kwargs):
        """ Convert any representation of an accounting tax line ('record') into a python
        dictionary that will be used to use by `_prepare_tax_lines` to detect which tax line
        could be updated, the ones to be created and the ones to be deleted.
        We can't use directly an account.move.line because this is also used by
        - expense (to create the journal entry)
        - the bank reconciliation widget
        All fields in this list are the same as the corresponding fields defined in account.move.line.

        The mechanism is the same as '_prepare_base_line_for_taxes_computation'.

        [!] Only added python-side.

        :param record:  A representation of a business object a.k.a a record or a dictionary.
        :param kwargs:  The extra values to override some values that will be taken from the record.
        :return:        A dictionary representing a tax line.
        """
        def load(field, fallback):
            return self._get_base_line_field_value_from_record(record, field, kwargs, fallback)

        currency = (
            load('currency_id', None)
            or load('company_currency_id', None)
            or load('company_id', self.env['res.company']).currency_id
            or self.env['res.currency']
        )

        return {
            **kwargs,
            'record': record,
            'id': load('id', 0),
            'tax_repartition_line_id': load('tax_repartition_line_id', self.env['account.tax.repartition.line']),
            'group_tax_id': load('group_tax_id', self.env['account.tax']),
            'tax_ids': load('tax_ids', self.env['account.tax']),
            'tax_tag_ids': load('tax_tag_ids', self.env['account.account.tag']),
            'currency_id': currency,
            'partner_id': load('partner_id', self.env['res.partner']),
            'account_id': load('account_id', self.env['account.account']),
            'analytic_distribution': load('analytic_distribution', None),
            'sign': load('sign', 1.0),
            'amount_currency': load('amount_currency', 0.0),
            'balance': load('balance', 0.0),
        }

    @api.model
    def _add_tax_details_in_base_line(self, base_line, company, rounding_method=None):
        """ Perform the taxes computation for the base line and add it to the base line under
        the 'tax_details' key. Those values are rounded or not depending of the tax calculation method.
        If you need to compute monetary fields with that, you probably need to call
        '_round_base_lines_tax_details' after this method.

        The added tax_details is a dictionary containing:
        raw_total_excluded_currency:    The total without tax expressed in foreign currency.
        raw_total_excluded:             The total without tax expressed in local currency.
        raw_total_included_currency:    The total tax included expressed in foreign currency.
        raw_total_included:             The total tax included expressed in local currency.
        taxes_data:                     A list of python dictionary containing the taxes_data returned by '_get_tax_details' but
                                        with the amounts expressed in both currencies:
            raw_tax_amount_currency         The tax amount expressed in foreign currency.
            raw_tax_amount                  The tax amount expressed in local currency.
            raw_base_amount_currency        The tax base amount expressed in foreign currency.
            raw_base_amount                 The tax base amount expressed in local currency.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_line:       A base line generated by '_prepare_base_line_for_taxes_computation'.
        :param company:         The company owning the base line.
        :param rounding_method: The rounding method to be used. If not specified, it will be taken from the company.
        """
        rounding_method = rounding_method or company.tax_calculation_rounding_method
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
        """ Shortcut to call '_add_tax_details_in_base_line' on multiple base lines at once.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:  A list of base lines.
        :param company:     The company owning the base lines.
        """
        for base_line in base_lines:
            self._add_tax_details_in_base_line(base_line, company)

    @api.model
    def _normalize_target_factors(self, target_factors):
        """ Normalize the factors passed as parameter to have a distribution having a sum of 1.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param target_factors:      A list of dictionary containing at least 'factor' being the weight
                                    defining how much delta will be allocated to this factor.
        :return:                    A list of tuple <index, normalized_factor> for each 'target_factors' passed as parameter.
        """
        factors = [(i, abs(target_factor['factor'])) for i, target_factor in enumerate(target_factors)]
        factors.sort(key=lambda x: x[1], reverse=True)
        sum_of_factors = sum(x[1] for x in factors)
        return [(i, factor / sum_of_factors if sum_of_factors else 1 / len(factors)) for i, factor in factors]

    @api.model
    def _distribute_delta_amount_smoothly(self, precision_digits, delta_amount, target_factors):
        """ Distribute 'delta_amount' across the factors passed as parameter.

        For example, if 'delta_amount' = 0.03 and precision_digits is 3 and target factors is a list of 3 factors:
        a) {'factor': 0.4}
        b) {'factor': 0.3}
        c) {'factor': 0.3}
        ... it means the delta will be distributed first on a) then b) then c).
        Since precision_digits = 3, it means we have a delta of "30" tenth of a hundred to be distributed.
        a) will take 30 * 0.4 = 12 units.
        b & c) will take 30 * 0.3 = 9 units each.
        The result of this method will be [0.012, 0.009, 0.009].

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param precision_digits:    The decimal places of the delta.
        :param delta_amount:        The delta amount to be distributed.
        :param target_factors:      A list of dictionary containing at least 'factor' being the weight
                                    defining how much delta will be allocated to this factor.
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
        # There are sorted by the biggest first.
        # Since the factors are normalized, the residual number of cents can't be higher than the number of factors.
        for i in range(remaining_errors):
            amounts_to_distribute[factors[i][0]] += sign * precision_rounding

        return amounts_to_distribute

    @api.model
    def _round_tax_details_tax_amounts(self, base_lines, company, mode='mixed'):
        """ Dispatch the delta in term of tax amounts across the tax details when dealing with the 'round_globally' method.
        Suppose 2 lines:
        - quantity=12.12, price_unit=12.12, tax=23%
        - quantity=12.12, price_unit=12.12, tax=23%
        The tax of each line is computed as round(12.12 * 12.12 * 0.23) = 33.79
        The expected tax amount of the whole document is round(12.12 * 12.12 * 0.23 * 2) = 67.57
        The delta in term of tax amount is 67.57 - 33.79 - 33.79 = -0.01

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company owning the base lines.
        :param mode:                The mode to round taxes:
            * excluded:                 Round base and tax independently.
            * included:                 Round base + tax, then subtract the tax and round the base according the remaining amount.
            * mixed:                    Round 'excluded' or 'included' depending if the tax is price-included or not.
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
        """ Additional global rounding depending on if the taxes are included or excluded in price.

        This method does not modify the rounding in `taxes_data`, rather it computes an adjustment
        for `tax_details['total_excluded{_currency}']` and stores it as `tax_details['delta_total_excluded{_currency}']`.

        Suppose all taxes are price-included.
        Suppose two price-included taxes of 10%.
        Suppose a line having price_unit=100.0.
        The tax amount is computed as 100.0 / 1.2 * 0.1 = 8.333333333
        The base amount is computed as 100.0 - (2 * 8.333333333) = 83.333333334
        Without doing anything, we end up with a base of 83.33 and 2 * 8.33 as tax amounts.
        83.33 + 8.33 + 8.33 = 99.99.
        However, since all tax are price-included, we expect a base amount of 83.34 to reach the
        original 100.0.

        Manage price-excluded taxes.
        Suppose 2 lines, both having quantity=12.12, price_unit=12.12, tax=23%
        The base amount of each line is computed as round(12.12 * 12.12) = 146.89
        The expected base amount of the whole document is round(12.12 * 12.12 * 2) = 293.79
        The delta in term of base amount is 293.79 - 146.89 - 146.89 = 0.01

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company owning the base lines.
        :param mode:                The mode to round taxes:
            * excluded:                 Round base and tax independently.
            * included:                 Round base + tax, then subtract the tax and round the base according the remaining amount.
            * mixed:                    Round 'excluded' or 'included' depending if the tax is price-included or not.
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
                    # Price-excluded rounding.
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
                    # Price-included rounding.
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
        At this point, everything is rounded and won't change anymore.

        [!] Only added python-side.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company owning the base lines.
        :param tax_lines:           A optional list of base lines generated using the '_prepare_tax_line_for_taxes_computation'
                                    method. If specified, the tax amounts will be computed based on those existing tax lines.
                                    It's used to keep the manual tax amounts set by the user.
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
        """ Round the 'tax_details' added to base_lines with the '_add_accounting_data_to_base_line_tax_details'.
        This method performs all the rounding and take care of rounding issues that could appear when using the
        'round_globally' tax computation method, specially if some price included taxes are involved.

        This method copies all float prefixed with 'raw_' in the tax_details to the corresponding float without 'raw_'.
        In almost all countries, the round globally should be the tax computation method.
        When there is an EDI, we need the raw amounts to be reported with more decimals (usually 6 to 8).
        So if you need to report the price excluded amount for a single line, you need to use
        'raw_total_excluded_currency' / 'raw_total_excluded' instead of 'total_excluded_currency' / 'total_excluded' because
        the latest are rounded. In short, rounding yourself the amounts is probably a mistake and you are probably adding some
        rounding issues in your code.

        The rounding is made by aggregating the raw amounts per tax first.
        Then we round the total amount per tax, same for each tax amount in each base lines.
        Finally, we distribute the delta on each base lines.
        The delta is available in 'delta_total_excluded_currency' / 'delta_total_excluded' in each base line.

        Let's take an example using round globally.
        Suppose two lines:
        l1: price_unit = 21.53, tax = 21% incl
        l2: price_unit = 21.53, tax = 21% incl

        The raw_total_excluded is computed as 21.53 / 1.21 = 17.79338843
        The total_excluded is computed as round(17.79338843) = 17.79
        The total raw_base_amount for 21% incl is computed as 17.79338843 * 2 = 35.58677686
        The total base_amount for 21% incl is round(35.58677686) = 35.59
        The delta_base_amount is computed as 35.59 - 17.79 - 17.79 = 0.01 and will be added on l1.

        For the tax amounts:
        The raw_tax_amount is computed as 21.53 / 1.21 * 0.21 = 3.73661157
        The tax_amount is computed as round(3.73661157) = 3.74
        The total raw_tax_amount for 21% incl is computed as 3.73661157 * 2 = 7.473223141
        The total tax_amount for 21% incl is computed as round(7.473223141) = 7.47
        The delta amount for 21% incl is computed as 7.47 - 3.74 - 3.74 = -0.01 and will be added to the corresponding
        tax_data in l1.

        If l1 and l2 are invoice lines, the result will be:
        l1: price_unit = 21.53, tax = 21% incl, price_subtotal = 17.79, price_total = 21.53, balance = 17.80
        l2: price_unit = 21.53, tax = 21% incl, price_subtotal = 17.79, price_total = 21.53, balance = 17.79
        To compute the tax lines, we use the tax details in base_line['tax_details']['taxes_data'] that contain
        respectively 3.73 + 3.74 = 7.47.
        Since the untaxed amount of the invoice is computed based on the accounting balance:
        amount_untaxed = 17.80 + 17.79 = 35.59
        amount_tax = 7.47
        amount_total = 21.53 + 21.53 = 43.06

        The amounts are globally correct because 35.59 * 0.21 = 7.4739 ~= 7.47.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company owning the base lines.
        :param tax_lines:           A optional list of base lines generated using the '_prepare_tax_line_for_taxes_computation'
                                    method. If specified, the tax amounts will be computed based on those existing tax lines.
                                    It's used to keep the manual tax amounts set by the user.
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

    @api.model
    def _prepare_base_line_grouping_key(self, base_line):
        """ Used by '_prepare_tax_lines' to build the accounting grouping key to generate the tax lines.
        This method takes all relevant fields from the base line that will be used to build the grouping_key.

        [!] Only added python-side.

        :param base_line: A base line generated by '_prepare_base_line_for_taxes_computation'.
        :return: The grouping key to generate the tax line for a single base line.
        """
        return {
            'partner_id': base_line['partner_id'].id,
            'currency_id': base_line['currency_id'].id,
            'analytic_distribution': base_line['analytic_distribution'],
            'account_id': base_line['account_id'].id,
            'tax_ids': [Command.set(base_line['tax_ids'].ids)],
        }

    @api.model
    def _prepare_base_line_tax_repartition_grouping_key(self, base_line, base_line_grouping_key, tax_data, tax_rep_data):
        """ Used by '_prepare_tax_lines' to build the accounting grouping key to generate the tax lines.
        This method adds all relevant fields from a single tax data to the grouping key.

        [!] Only added python-side.

        :param base_line:               A base line generated by '_prepare_base_line_for_taxes_computation'.
        :param base_line_grouping_key:  The grouping key created by '_prepare_base_line_grouping_key'.
        :param tax_data:                One of the tax data in base_line['tax_details']['taxes_data'].
        :param tax_rep_data:            One of the tax repartition data in tax_data['tax_reps_data'].
        :return: The grouping key to generate the tax line for tax repartition line.
        """
        tax = tax_data['tax']
        tax_rep = tax_rep_data['tax_rep']
        return {
            **base_line_grouping_key,
            'tax_repartition_line_id': tax_rep.id,
            'partner_id': base_line['partner_id'].id,
            'currency_id': base_line['currency_id'].id,
            'group_tax_id': tax_data['group'].id,
            'analytic_distribution': (
                base_line_grouping_key['analytic_distribution']
                if tax.analytic or not tax_rep.use_in_tax_closing
                else False
            ),
            'account_id': tax_rep_data['account'].id or base_line_grouping_key['account_id'],
            'tax_ids': [Command.set(tax_rep_data['taxes'].ids)],
            'tax_tag_ids': [Command.set(tax_rep_data['tax_tags'].ids)],
            '__keep_zero_line': False,
        }

    @api.model
    def _prepare_tax_line_repartition_grouping_key(self, tax_line):
        """ Used by '_prepare_tax_lines' to build the accounting grouping key to know if the tax line could be updated
        or not when recomputing the tax lines.
        Take care this method should remain consistent regarding the grouping key built from the base line.

        [!] Only added python-side.

        :param tax_line: A tax line generated by '_prepare_tax_line_for_taxes_computation'.
        :return: The grouping key for the tax line passed as parameter.
        """
        return {
            'tax_repartition_line_id': tax_line['tax_repartition_line_id'].id,
            'partner_id': tax_line['partner_id'].id,
            'currency_id': tax_line['currency_id'].id,
            'group_tax_id': tax_line['group_tax_id'].id,
            'analytic_distribution': tax_line['analytic_distribution'],
            'account_id': tax_line['account_id'].id,
            'tax_ids': [Command.set(tax_line['tax_ids'].ids)],
            'tax_tag_ids': [Command.set(tax_line['tax_tag_ids'].ids)],
        }

    @api.model
    def _add_accounting_data_to_base_line_tax_details(self, base_line, company, include_caba_tags=False):
        """ Add all informations about repartition lines to base_line['tax_details']['taxes_data'].

        Considering a single tax_data, this method adds 'tax_reps_data', being a list of python dictionaries containing:
            tax_rep:                The account.tax.repartition.line record.
            tax_amount_currency:    The tax amount expressed in foreign currency.
            tax_amount:             The tax amount expressed in local currency.
            account:                The accounting account record to consider for this tax repartition line.
            taxes:                  The taxes to be set on the tax line if the tax affects the base of subsequent taxes.
            tax_tags:               The tags for the tax report.
            grouping_key:           The grouping key used to generate this tax line.

        This method also adds 'tax_tag_ids' to the base line containing the tags for the tax report.

        [!] Only added python-side.

        :param base_line:               A base line generated by '_prepare_base_line_for_taxes_computation'.
        :param company:                 The company owning the base line.
        :param include_caba_tags:       Indicate if the cash basis tags need to be taken into account.
        """
        is_refund = base_line['is_refund']
        currency = base_line['currency_id']
        product = base_line['product_id']
        company_currency = company.currency_id
        if is_refund:
            repartition_lines_field = 'refund_repartition_line_ids'
        else:
            repartition_lines_field = 'invoice_repartition_line_ids'

        # Tags on the base line.
        taxes_data = base_line['tax_details']['taxes_data']
        base_line['tax_tag_ids'] = self.env['account.account.tag']
        product_tags = self.env['account.account.tag']
        if product:
            countries = {tax_data['tax'].country_id for tax_data in taxes_data}
            countries.add(False)
            product_tags = product.sudo().account_tag_ids
            base_line['tax_tag_ids'] |= product_tags

        for tax_data in taxes_data:
            tax = tax_data['tax']

            # Tags on the base line.
            if not tax_data['is_reverse_charge'] and (include_caba_tags or tax.tax_exigibility == 'on_invoice'):
                base_line['tax_tag_ids'] |= tax[repartition_lines_field].filtered(lambda x: x.repartition_type == 'base').tag_ids

            # Compute repartition lines amounts.
            if tax_data['is_reverse_charge']:
                tax_reps = tax[repartition_lines_field].filtered(lambda x: x.repartition_type == 'tax' and x.factor < 0.0)
                tax_rep_sign = -1.0
            else:
                tax_reps = tax[repartition_lines_field].filtered(lambda x: x.repartition_type == 'tax' and x.factor >= 0.0)
                tax_rep_sign = 1.0

            total_tax_rep_amounts = {
                'tax_amount_currency': 0.0,
                'tax_amount': 0.0,
            }
            tax_reps_data = tax_data['tax_reps_data'] = []
            for tax_rep in tax_reps:
                tax_amount_currency = tax_data.get('tax_amount_currency')

                if self.env.context.get('compute_all_use_raw_base_lines'):
                    tax_amount_currency = tax_data.get('raw_tax_amount_currency')

                tax_rep_data = {
                    'tax_rep': tax_rep,
                    'tax_amount_currency': currency.round(tax_amount_currency * tax_rep.factor * tax_rep_sign),
                    'tax_amount': company_currency.round(tax_data['tax_amount'] * tax_rep.factor * tax_rep_sign),
                    'account': tax_rep._get_aml_target_tax_account(force_caba_exigibility=include_caba_tags) or base_line['account_id'],
                }
                total_tax_rep_amounts['tax_amount_currency'] += tax_rep_data['tax_amount_currency']
                total_tax_rep_amounts['tax_amount'] += tax_rep_data['tax_amount']
                tax_reps_data.append(tax_rep_data)

            # Distribute the delta on the repartition lines.
            sorted_tax_reps_data = sorted(
                tax_reps_data,
                key=lambda tax_rep: (-abs(tax_rep['tax_amount_currency']), -abs(tax_rep['tax_amount'])),
            )
            for delta_suffix, delta_currency in (
                ('_currency', currency),
                ('', company_currency),
            ):
                field = f'tax_amount{delta_suffix}'
                tax_amount = tax_data.get(field)
                if self.env.context.get('compute_all_use_raw_base_lines'):
                    tax_amount = tax_data.get(f"raw_{field}")

                delta_amount = tax_amount - total_tax_rep_amounts[field]
                target_factors = [
                    {
                        'factor': tax_rep_data[field],
                        'tax_rep_data': tax_rep_data,
                    }
                    for tax_rep_data in sorted_tax_reps_data
                ]
                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=delta_currency.decimal_places,
                    delta_amount=delta_amount,
                    target_factors=target_factors,
                )
                for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                    target_factor['tax_rep_data'][field] += amount_to_distribute

        subsequent_tags_per_tax = defaultdict(lambda: self.env['account.account.tag'])
        for tax_data in reversed(taxes_data):
            tax = tax_data['tax']

            for tax_rep_data in tax_data['tax_reps_data']:
                tax_rep = tax_rep_data['tax_rep']

                # Compute subsequent taxes/tags.
                tax_rep_data['taxes'] = tax_data['taxes']
                tax_rep_data['tax_tags'] = product_tags
                if include_caba_tags or tax.tax_exigibility == 'on_invoice':
                    tax_rep_data['tax_tags'] |= tax_rep.tag_ids
                if tax.include_base_amount:
                    for other_tax, tags in subsequent_tags_per_tax.items():
                        if tax != other_tax:
                            tax_rep_data['tax_tags'] |= tags

                # Add the accounting grouping_key to create the tax lines.
                base_line_grouping_key = self._prepare_base_line_grouping_key(base_line)
                tax_rep_data['grouping_key'] = self._prepare_base_line_tax_repartition_grouping_key(
                    base_line,
                    base_line_grouping_key,
                    tax_data,
                    tax_rep_data,
                )

            if tax.is_base_affected:
                if include_caba_tags or tax.tax_exigibility == 'on_invoice':
                    subsequent_tags_per_tax[tax] |= tax[repartition_lines_field].filtered(lambda x: x.repartition_type == 'base').tag_ids

    @api.model
    def _add_accounting_data_in_base_lines_tax_details(self, base_lines, company, include_caba_tags=False):
        """ Shortcut to call '_add_accounting_data_to_base_line_tax_details' on multiple base lines at once.

        [!] Only added python-side.

        :param base_lines:          A list of base lines.
        :param company:             The company owning the base lines.
        :param include_caba_tags:   Indicate if the cash basis tags need to be taken into account.
        """
        for base_line in base_lines:
            self._add_accounting_data_to_base_line_tax_details(base_line, company, include_caba_tags=include_caba_tags)

    # -------------------------------------------------------------------------
    # AGGREGATOR OF TAX DETAILS
    # -------------------------------------------------------------------------

    @api.model
    def _aggregate_base_line_tax_details(self, base_line, grouping_function):
        """ Aggregate the tax details for a single line according a custom grouping function passed as parameter.
        This method is mainly use for EDI to report some data per line. Most of the time, having the amounts grouped
        by tax is not enough because some details should be excluded, aggregated together or just moved into a separated section
        having another grouping key.

        In case the base_line has no tax, the grouping_function is called with an empty tax_data to get the grouping key for the line.

        Don't forget to call '_add_tax_details_in_base_lines' and '_round_base_lines_tax_details' before calling this method.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_line:           A base line generated by '_prepare_base_line_for_taxes_computation'.
        :param grouping_function:   A function taking <base_line, tax_data> as parameter and returning anything
                                    that could be used as key in a dictionary.
                                    Note: you must never return None (explanation in the docstring above).
        :return: A mapping <grouping_key, amounts> where:
            grouping_key                is the grouping_key returned by the 'grouping_function' or 'None'.
            amounts                     is a dictionary containing:
                base_amount_currency:           The base amount of this grouping key expressed in foreign currency.
                base_amount:                    The base amount of this grouping key expressed in local currency.
                raw_base_amount_currency:       The base amount of this grouping key expressed in foreign currency before any rounding.
                raw_base_amount:                The base amount of this grouping key expressed in local currency before any rounding.
                target_base_amount_currency:    The same as 'raw_base_amount_currency' but considering the manual amounts.
                target_base_amount:             The same as 'raw_base_amount' but considering the manual amounts.
                tax_amount_currency:            The tax amount of this grouping key expressed in foreign currency.
                tax_amount:                     The tax amount of this grouping key expressed in local currency.
                raw_tax_amount_currency:        The tax amount of this grouping key expressed in foreign currency before any rounding.
                raw_tax_amount:                 The tax amount of this grouping key expressed in local currency before any rounding.
                target_tax_amount_currency:     The same as 'raw_tax_amount_currency' but considering the manual amounts.
                target_tax_amount:              The same as 'raw_tax_amount' but considering the manual amounts.
                total_excluded_currency:        The delta base amount for the base line involved in this grouping key expressed
                                                in foreign currency.
                total_excluded:                 The delta base amount for the base line involved in this grouping key expressed
                                                in local currency.
                raw_total_excluded_currency:    The delta base amount for the base line involved in this grouping key expressed
                                                in foreign currency before any rounding.
                raw_total_excluded:             The delta base amount for the base line involved in this grouping key expressed
                                                in local currency before any rounding.
                target_total_excluded_currency: The same as 'raw_total_excluded_currency' but considering the manual amounts.
                target_total_excluded:          The same as 'raw_total_excluded' but considering the manual amounts.
                taxes_data:                     The subset of base_line['tax_details']['taxes_data'] aggregated under this grouping_key.
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
        """ Shortcut to call '_aggregate_base_line_tax_details' on multiple base lines at once.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          A list of base lines.
        :param grouping_function:   See '_aggregate_base_line_tax_details'.
        :return                     A list of tuple <base_line, results> that associates the result of
                                    '_aggregate_base_line_tax_details' for each base line independently.
        """
        return [
            (base_line, self._aggregate_base_line_tax_details(base_line, grouping_function))
            for base_line in base_lines
        ]

    @api.model
    def _aggregate_base_lines_aggregated_values(self, base_lines_aggregated_values):
        """ Aggregate the values returned by '_aggregate_base_lines_tax_details' for the whole document.
        Most of the time, in EDI, you have to report unrounded amounts for each base line first and then,
        you need to report all rounded amounts for the whole business document.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines_aggregated_values:    The result of '_aggregate_base_lines_tax_details'.
        :return: A mapping <grouping_key, amounts> where:
            grouping_key                is the grouping_key returned by the 'grouping_function' or 'None'.
            amounts                     is a dictionary containing:
                base_amount_currency:       The base amount of this grouping key expressed in foreign currency.
                base_amount:                The base amount of this grouping key expressed in local currency.
                raw_base_amount_currency:   The base amount of this grouping key expressed in foreign currency before any rounding.
                raw_base_amount:            The base amount of this grouping key expressed in local currency before any rounding.
                tax_amount_currency:        The tax amount of this grouping key expressed in foreign currency.
                tax_amount:                 The tax amount of this grouping key expressed in local currency.
                raw_tax_amount_currency:    The tax amount of this grouping key expressed in foreign currency before any rounding.
                raw_tax_amount:             The tax amount of this grouping key expressed in local currency before any rounding.
                total_excluded_currency:    The delta base amount for the base line involved in this grouping key expressed
                                            in foreign currency.
                total_excluded:             The delta base amount for the base line involved in this grouping key expressed
                                            in local currency.
                base_line_x_taxes_data:     A list of tuple <base_line, taxes_data> that associates for each base_line the
                                            subset of base_line['tax_details']['taxes_data'] aggregated under this grouping_key.
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

    # -------------------------------------------------------------------------
    # TAX TOTALS SUMMARY
    # -------------------------------------------------------------------------

    @api.model
    def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
        """ Compute the tax totals details for the business documents.

        Don't forget to call '_add_tax_details_in_base_lines' and '_round_base_lines_tax_details' before calling this method.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param currency:            The tax totals is only available when all base lines share the same currency.
                                    Since the tax totals can be computed when there is no base line at all, a currency must be
                                    specified explicitely for that case.
        :param company:             The company owning the base lines.
        :param cash_rounding:       A optional account.cash.rounding object. When specified, the delta base amount added
                                    to perform the cash rounding is specified in the results.
        :return: A dictionary containing:
            currency_id:                            The id of the currency used.
            currency_pd:                            The currency rounding (to be used js-side by the widget).
            company_currency_id:                    The id of the company's currency used.
            company_currency_pd:                    The company's currency rounding (to be used js-side by the widget).
            has_tax_groups:                         Flag indicating if there is at least one involved tax group.
            same_tax_base:                          Flag indicating the base amount of all tax groups are the same and it's
                                                    redundant to display them.
            base_amount_currency:                   The untaxed amount expressed in foreign currency.
            base_amount:                            The untaxed amount expressed in local currency.
            tax_amount_currency:                    The tax amount expressed in foreign currency.
            tax_amount:                             The tax amount expressed in local currency.
            total_amount_currency:                  The total amount expressed in foreign currency.
            total_amount:                           The total amount expressed in local currency.
            cash_rounding_base_amount_currency:     The delta added by 'cash_rounding' expressed in foreign currency.
                                                    If there is no amount added, the key is not in the result.
            cash_rounding_base_amount:              The delta added by 'cash_rounding' expressed in local currency.
                                                    If there is no amount added, the key is not in the result.
            subtotals:                              A list of subtotal (like "Untaxed Amount"), each one being a python dictionary
                                                    containing:
                base_amount_currency:                   The base amount expressed in foreign currency.
                base_amount:                            The base amount expressed in local currency.
                tax_amount_currency:                    The tax amount expressed in foreign currency.
                tax_amount:                             The tax amount expressed in local currency.
                tax_groups:                             A list of python dictionary, one for each tax group, containing:
                    id:                                     The id of the account.tax.group.
                    group_name:                             The name of the group.
                    group_label:                            The short label of the group to be displayed on POS receipt.
                    involved_tax_ids:                       A list of the tax ids aggregated in this tax group.
                    base_amount_currency:                   The base amount expressed in foreign currency.
                    base_amount:                            The base amount expressed in local currency.
                    tax_amount_currency:                    The tax amount expressed in foreign currency.
                    tax_amount:                             The tax amount expressed in local currency.
                    display_base_amount_currency:           The base amount to display expressed in foreign currency.
                                                            The flat base amount and the amount to be displayed are sometimes different
                                                            (e.g. division/fixed taxes).
                    display_base_amount:                    The base amount to display expressed in local currency.
                                                            The flat base amount and the amount to be displayed are sometimes different
                                                            (e.g. division/fixed taxes).
                    non_deductible_tax_amount_currency:     The tax delta added by 'non_deductible' expressed in foreign currency.
                                                            If there is no amount added, the key is not in the result.
                    non_deductible_tax_amount:              The tax delta added by 'non_deductible' expressed in local currency.
                                                            If there is no amount added, the key is not in the result.
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
                        # Failed to apply the cash rounding since there is no tax.
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

        # Non deductible lines (this part is not implemented in the JS-part of the tax total summary computation)
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
        """ Helper to post-process the tax totals and wrap some tax groups into the base amount.
        It's used in some localizations to exclude some taxes from the details.

        [!] Only added python-side.

        :param tax_totals:          The tax totals generated by '_get_tax_totals_summary'.
        :param ids_to_exclude:      The ids of the tax groups to exclude.
        :return:                    A new tax totals without the excluded ids.
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

    # -------------------------------------------------------------------------
    # TAX LINES GENERATION
    # -------------------------------------------------------------------------

    @api.model
    def _prepare_tax_lines(self, base_lines, company, tax_lines=None):
        """ Prepare the tax journal items for the base lines.

        After calling '_add_tax_details_in_base_lines', the tax details is there on base lines.
        After calling '_round_base_lines_tax_details', the tax details is now rounded.
        After calling '_add_accounting_data_in_base_lines_tax_details', each tax_data in the tax details
        contains all accounting informations about the repartition lines.

        When calling this method, all 'tax_reps_data' in each 'tax_data' will be aggregated all together
        and rounded. The total tax amount will not change whatever the number of involved accounting
        grouping keys.
        The 'sign' value in base lines is very important for this method because that key decide the sign
        of the 'amount_currency'/'balance' of the base lines/tax lines to be updated/created.

        Don't forget to call '_add_tax_details_in_base_lines', '_round_base_lines_tax_details' and
        '_add_accounting_data_in_base_lines_tax_details' before calling this method.

        [!] Only added python-side.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company owning the base lines.
        :param tax_lines:           A optional list of base lines generated using the '_prepare_tax_line_for_taxes_computation'
                                    method. If specified, this method will indicate which tax lines must be deleted or updated instead
                                    of creating again all tax lines everytime.
        :return: The base amounts for base lines and the full diff about tax lines as a dictionary containing:
            tax_lines_to_add:       A list of values to be passed to account.move.line's create function.
            tax_lines_to_delete:    The list of tax lines to be removed.
            tax_lines_to_update:    A list of tuple <tax_line, grouping_key, amounts> where:
                tax_line                is the tax line to be updated,
                grouping_key            is the accounting grouping key matching the tax line and used to determine the tax line can be
                                        updated instead of created again,
                amounts                 is a dictionary containing the new values for 'tax_base_amount', 'amount_currency', 'balance'.
            base_lines_to_update:   A list of tuple <base_line, amounts> where:
                base_line               is the base line to be updated.
                amounts                 is a dictionary containing the new values for 'tax_tag_ids', 'amount_currency', 'balance'.
        """
        tax_lines_mapping = defaultdict(lambda: {
            'tax_base_amount': 0.0,
            'amount_currency': 0.0,
            'balance': 0.0,
        })

        base_lines_to_update = []
        for base_line in base_lines:
            sign = base_line['sign']
            tax_details = base_line['tax_details']
            base_lines_to_update.append((
                base_line,
                {
                    'tax_tag_ids': [Command.set(base_line['tax_tag_ids'].ids)],
                    'amount_currency': sign * (tax_details['total_excluded_currency'] + tax_details['delta_total_excluded_currency']),
                    'balance': sign * (tax_details['total_excluded'] + tax_details['delta_total_excluded']),
                },
            ))
            for tax_data in tax_details['taxes_data']:
                tax = tax_data['tax']
                for tax_rep_data in tax_data['tax_reps_data']:
                    grouping_key = frozendict(tax_rep_data['grouping_key'])
                    tax_line = tax_lines_mapping[grouping_key]
                    tax_line['name'] = base_line.get('manual_tax_line_name', tax.name)
                    tax_line['tax_base_amount'] += sign * tax_data['base_amount']
                    tax_line['amount_currency'] += sign * tax_rep_data['tax_amount_currency']
                    tax_line['balance'] += sign * tax_rep_data['tax_amount']

        # Remove tax lines having a zero amount.
        tax_lines_mapping = {
            frozendict({grouping_k: k[grouping_k] for grouping_k in k if not grouping_k.startswith('__')}): v
            for k, v in tax_lines_mapping.items()
            if (
                k['__keep_zero_line'] or (
                    not self.env['res.currency'].browse(k['currency_id']).is_zero(v['amount_currency'])
                    or not company.currency_id.is_zero(v['balance'])
                )
            )
        }

        # Compute 'tax_lines_to_update' / 'tax_lines_to_delete' / 'tax_lines_to_add'.
        tax_lines_to_update = []
        tax_lines_to_delete = []
        for tax_line in tax_lines or []:
            grouping_key = frozendict(self._prepare_tax_line_repartition_grouping_key(tax_line))
            if grouping_key in tax_lines_mapping and grouping_key not in tax_lines_to_update:
                amounts = tax_lines_mapping.pop(grouping_key)
                tax_lines_to_update.append((tax_line, grouping_key, amounts))
            else:
                tax_lines_to_delete.append(tax_line)
        tax_lines_to_add = [{**grouping_key, **values} for grouping_key, values in tax_lines_mapping.items()]

        return {
            'tax_lines_to_add': tax_lines_to_add,
            'tax_lines_to_delete': tax_lines_to_delete,
            'tax_lines_to_update': tax_lines_to_update,
            'base_lines_to_update': base_lines_to_update,
        }

    # -------------------------------------------------------------------------
    # ADVANCED LINES MANIPULATION HELPERS
    # -------------------------------------------------------------------------

    def _can_be_discounted(self):
        """ Detect if a tax is affected by the discount.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :return: A boolean.
        """
        self.ensure_one()
        return self.amount_type not in ('fixed', 'code')

    @api.model
    def _merge_tax_details(self, tax_details_1, tax_details_2):
        """ Helper merging 2 tax details together coming from base lines.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param tax_details_1: First tax details.
        :param tax_details_2: Second tax details.
        :return: A new tax details combining the 2 passed as parameter.
        """
        results = {
            f'{prefix}{field}{suffix}': tax_details_1[f'{prefix}{field}{suffix}'] + tax_details_2[f'{prefix}{field}{suffix}']
            for prefix in ('raw_', '')
            for field in ('total_excluded', 'total_included')
            for suffix in ('_currency', '')
        }
        for suffix in ('_currency', ''):
            field = f'delta_total_excluded{suffix}'
            results[field] = tax_details_1[field] + tax_details_2[field]

        agg_taxes_data = {}
        for tax_details in (tax_details_1, tax_details_2):
            for tax_data in tax_details['taxes_data']:
                tax = tax_data['tax']
                if tax in agg_taxes_data:
                    agg_tax_data = agg_taxes_data[tax]
                    for prefix in ('raw_', ''):
                        for suffix in ('_currency', ''):
                            for field in ('base_amount', 'tax_amount'):
                                field_with_prefix = f'{prefix}{field}{suffix}'
                                agg_tax_data[field_with_prefix] += tax_data[field_with_prefix]
                else:
                    agg_taxes_data[tax] = dict(tax_data)
        results['taxes_data'] = list(agg_taxes_data.values())

        # In case there is some taxes that are in tax_details_1 but not on tax_details_2,
        # we have to shift manually the base amount. It happens with fixed taxes in which the base
        # is meaningless but still used in the computations.
        taxes_data_in_2 = {tax_data['tax'] for tax_data in tax_details_2['taxes_data']}
        not_discountable_taxes_data = {
            tax_data['tax']
            for tax_data in tax_details_1['taxes_data']
            if tax_data['tax'] not in taxes_data_in_2
        }
        for tax_data in results['taxes_data']:
            if tax_data['tax'] in not_discountable_taxes_data:
                for suffix in ('_currency', ''):
                    for prefix in ('raw_', ''):
                        tax_data[f'{prefix}base_amount{suffix}'] += tax_details_2[f'{prefix}total_excluded{suffix}']
                    tax_data[f'base_amount{suffix}'] += tax_details_2[f'delta_total_excluded{suffix}']

        return results

    @api.model
    def _fix_base_lines_tax_details_on_manual_tax_amounts(self, base_lines, company, filter_function=None):
        """ Store the tax details into manual_tax_amounts to fix the results.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:      A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:         The company owning the base lines.
        :param filter_function: An optional function taking <base_line, tax_data> as parameter and telling which tax will have
                                its amounts stored.
        """
        for base_line in base_lines:
            tax_details = base_line['tax_details']
            taxes_data = tax_details['taxes_data']
            if not taxes_data:
                continue

            base_line['manual_total_excluded_currency'] = (
                tax_details['total_excluded_currency']
                + tax_details['delta_total_excluded_currency']
            )
            base_line['manual_total_excluded'] = (
                tax_details['total_excluded']
                + tax_details['delta_total_excluded']
            )
            base_line['manual_tax_amounts'] = {}
            for tax_data in taxes_data:
                if tax_data['is_reverse_charge']:
                    continue
                tax = tax_data['tax']
                tax_id_str = str(tax.id)
                base_line['manual_tax_amounts'][tax_id_str] = {}
                if filter_function and not filter_function(base_line, tax_data):
                    continue

                base_line['manual_tax_amounts'][tax_id_str] = {
                    'tax_amount_currency': tax_data['tax_amount_currency'],
                    'tax_amount': tax_data['tax_amount'],
                    'base_amount_currency': tax_data['base_amount_currency'],
                    'base_amount': tax_data['base_amount'],
                }

    @api.model
    def _split_tax_data(self, base_line, tax_data, company, target_factors):
        """ Split a 'tax_data' in pieces according the factors passed as parameter.
        This method makes sure no amount is lost or gained during the process.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_line:       A base line.
        :param tax_data:        The 'tax_data' to split.
        :param company:         The company owning the base lines.
        :param target_factors:  A list of dictionary containing at least 'factor' being the weight
                                defining how much delta will be allocated to this factor.
        :return                 A list of 'tax_data' having the same size as 'target_factors'.
        """
        currency = base_line['currency_id']

        factors = self._normalize_target_factors(target_factors)

        new_taxes_data = []

        # Distribution of raw amounts.
        for _index, factor in factors:
            new_taxes_data.append({
                **tax_data,
                'raw_tax_amount_currency': factor * tax_data['raw_tax_amount_currency'],
                'raw_tax_amount': factor * tax_data['raw_tax_amount'],
                'raw_base_amount_currency': factor * tax_data['raw_base_amount_currency'],
                'raw_base_amount': factor * tax_data['raw_base_amount'],
            })

        # Distribution of rounded amounts.
        new_target_factors = [
            {
                'factor': target_factor['factor'],
                'tax_data': new_tax_data,
            }
            for new_tax_data, target_factor in zip(new_taxes_data, target_factors)
        ]

        for delta_currency_indicator, delta_currency in (
            ('_currency', currency),
            ('', company.currency_id),
        ):
            for prefix in ('tax', 'base'):
                field = f'{prefix}_amount{delta_currency_indicator}'
                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=delta_currency.decimal_places,
                    delta_amount=tax_data[field],
                    target_factors=new_target_factors,
                )
                for target_factor, amount_to_distribute in zip(new_target_factors, amounts_to_distribute):
                    new_tax_data = target_factor['tax_data']
                    new_tax_data[field] = amount_to_distribute
        return new_taxes_data

    @api.model
    def _split_tax_details(self, base_line, company, target_factors):
        """ Split the 'tax_details' in pieces according the factors passed as parameter.
        This method makes sure no amount is lost or gained during the process.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_line:       A base line.
        :param company:         The company owning the base lines.
        :param target_factors:  A list of dictionary containing at least 'factor' being the weight
                                defining how much delta will be allocated to this factor.
        :return                 A list of 'tax_details' having the same size as 'target_factors'.
        """
        currency = base_line['currency_id']
        tax_details = base_line['tax_details']

        factors = self._normalize_target_factors(target_factors)

        new_tax_details_list = []

        # Distribution of raw amounts.
        for _index, factor in factors:
            new_tax_details_list.append({
                'raw_total_excluded_currency': factor * tax_details['raw_total_excluded_currency'],
                'raw_total_excluded': factor * tax_details['raw_total_excluded'],
                'raw_total_included_currency': factor * tax_details['raw_total_included_currency'],
                'raw_total_included': factor * tax_details['raw_total_included'],
                'delta_total_excluded_currency': 0.0,
                'delta_total_excluded': 0.0,
                'taxes_data': [],
            })

        # Manage 'taxes_data'.
        for tax_data in tax_details['taxes_data']:
            new_taxes_data = self._split_tax_data(base_line, tax_data, company, target_factors)
            for new_tax_details, new_tax_data in zip(new_tax_details_list, new_taxes_data):
                new_tax_details['taxes_data'].append(new_tax_data)

        # Distribution of rounded amounts.
        for delta_currency_indicator, delta_currency in (
            ('_currency', currency),
            ('', company.currency_id),
        ):
            new_target_factors = [
                {
                    'factor': new_tax_details[f'raw_total_excluded{delta_currency_indicator}'],
                    'tax_details': new_tax_details,
                }
                for new_tax_details in new_tax_details_list
            ]
            field = f'total_excluded{delta_currency_indicator}'
            delta_amount = tax_details[field]
            amounts_to_distribute = self._distribute_delta_amount_smoothly(
                precision_digits=delta_currency.decimal_places,
                delta_amount=delta_amount,
                target_factors=new_target_factors,
            )
            for target_factor, amount_to_distribute in zip(new_target_factors, amounts_to_distribute):
                new_tax_details = target_factor['tax_details']
                new_tax_details[field] = amount_to_distribute

        # Manage 'total_included'.
        for new_tax_details in new_tax_details_list:
            for delta_currency_indicator in ('_currency', ''):
                new_tax_details[f'total_included{delta_currency_indicator}'] = (
                    new_tax_details[f'total_excluded{delta_currency_indicator}']
                    + sum(
                        new_tax_data[f'tax_amount{delta_currency_indicator}']
                        for new_tax_data in new_tax_details['taxes_data']
                    )
                )
        return new_tax_details_list

    @api.model
    def _split_base_line(self, base_line, company, target_factors, populate_function=None):
        """ Split a base lines into multiple ones. When computing taxes, the results should be
        exactly the same with a single base_line or after the split.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_line:           A base line.
        :param company:             The company owning the base line.
        :param target_factors:      A list of dictionary containing at least 'factor' being the weight
                                    defining how much delta will be allocated to this factor.
        :param populate_function:   An optional method to change the parameter of '_prepare_base_line_for_taxes_computation'
                                    when creating the new base lines from the one passed as parameter. This method takes
                                    the same parameter as '_prepare_base_line_for_taxes_computation'.
        :return:                    A list of base lines.
        """
        factors = self._normalize_target_factors(target_factors)

        # Split 'tax_details'.
        new_tax_details_list = self._split_tax_details(base_line, company, target_factors)

        # Split 'base_line'.
        new_base_lines = [None] * len(factors)
        for (index, factor), new_tax_details, target_factor in zip(factors, new_tax_details_list, target_factors):
            kwargs = {
                'price_unit': factor * base_line['price_unit'],
                'tax_details': new_tax_details,
            }
            if populate_function:
                populate_function(base_line, target_factor, kwargs)
            new_base_lines[index] = self._prepare_base_line_for_taxes_computation(base_line, **kwargs)
        return new_base_lines

    @api.model
    def _compute_subset_base_lines_total(self, base_lines, company):
        """ Compute the total of the lines passed as parameter.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        DEPRECATED: TO BE REMOVED IN MASTER

        :param base_lines:  A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:     The company owning the base lines.
        :return: The total.
        """
        base_amount_currency = 0.0
        tax_amount_currency = 0.0
        base_amount = 0.0
        tax_amount = 0.0
        tax_amounts_mapping = defaultdict(lambda: {
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
        })
        raw_total_included_currency = 0.0
        raw_total_included = 0.0
        for base_line in base_lines:
            tax_details = base_line['tax_details']
            base_amount_currency += tax_details['total_excluded_currency'] + tax_details['delta_total_excluded_currency']
            base_amount += tax_details['total_excluded'] + tax_details['delta_total_excluded']
            raw_total_included_currency += tax_details['raw_total_excluded_currency']
            raw_total_included += tax_details['raw_total_excluded']
            for tax_data in tax_details['taxes_data']:
                tax = tax_data['tax']
                if not tax._can_be_discounted():
                    continue

                tax_id_str = str(tax.id)
                tax_amount_currency += tax_data['tax_amount_currency']
                tax_amount += tax_data['tax_amount']
                tax_amounts_mapping[tax_id_str]['tax_amount_currency'] += tax_data['tax_amount_currency']
                tax_amounts_mapping[tax_id_str]['tax_amount'] += tax_data['tax_amount']
                raw_total_included_currency += tax_data['raw_tax_amount_currency']
                raw_total_included += tax_data['raw_tax_amount']
        return {
            'base_amount_currency': base_amount_currency,
            'tax_amount_currency': tax_amount_currency,
            'base_amount': base_amount,
            'tax_amount': tax_amount,
            'tax_amounts_mapping': tax_amounts_mapping,
            'raw_total_included_currency': raw_total_included_currency,
            'raw_total_included': raw_total_included,
            'rate': raw_total_included_currency / raw_total_included if raw_total_included else 0.0,
        }

    @api.model
    def _reduce_base_lines_with_grouping_function(self, base_lines, grouping_function=None, aggregate_function=None, computation_key=None):
        """ Create the new base lines that will get the discount.
        Since they no longer contain fixed taxes, we can remove the quantity and aggregate them depending on
        the grouping_function passed as parameter.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          The base lines to be aggregated.
        :param grouping_function:   An optional function taking a base line as parameter and returning a grouping key
                                    being the way the base lines will be aggregated all together.
                                    By default, the base lines will be aggregated by taxes.
        :param aggregate_function:  An optional function taking the 2 base lines as parameter to be aggregated together.
        :param computation_key:     The computation_key to be set on the aggregated base_lines.
        :return:                    The base lines aggregated.
        """
        aggregated_base_lines = {}
        base_line_map = {}
        for base_line in base_lines:
            price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
            new_base_line = self._prepare_base_line_for_taxes_computation(
                base_line,
                price_unit=base_line['quantity'] * price_unit_after_discount,
                quantity=1.0,
                discount=0.0,
            )
            grouping_key = {'tax_ids': new_base_line['tax_ids']}
            if grouping_function:
                grouping_key.update(grouping_function(new_base_line))
            grouping_key = frozendict(grouping_key)

            if base_line['analytic_distribution']:
                for account_id, distribution in base_line['analytic_distribution'].items():
                    aggregated_base_lines.setdefault(account_id, []).append(distribution)

            target_base_line = base_line_map.get(grouping_key)
            if target_base_line:
                target_base_line['price_unit'] += new_base_line['price_unit']
                target_base_line['tax_details'] = self._merge_tax_details(
                    tax_details_1=target_base_line['tax_details'],
                    tax_details_2=base_line['tax_details'],
                )
                if aggregate_function:
                    aggregate_function(target_base_line, base_line)
            else:
                target_base_line = self._prepare_base_line_for_taxes_computation(
                    new_base_line,
                    **grouping_key,
                    computation_key=computation_key,
                    tax_details={
                        **base_line['tax_details'],
                        'taxes_data': [dict(tax_data) for tax_data in base_line['tax_details']['taxes_data']],
                    },
                )
                base_line_map[grouping_key] = target_base_line
                if aggregate_function:
                    aggregate_function(target_base_line, base_line)
            aggregated_base_lines.setdefault(grouping_key, []).append(base_line)

        # Remove zero lines.
        base_line_map = {
            grouping_key: base_line
            for grouping_key, base_line in base_line_map.items()
            if not base_line['currency_id'].is_zero(base_line['price_unit'])
        }

        # Compute the analytic distribution for the new base line.
        # To do so, we have to aggregate the analytic distribution of each line that has been aggregated.
        # We need to take care about the negative lines but also of the negative distribution.
        # Suppose:
        # - line1 of 1000 having an analytic distribution of 100%
        # - line2 of -100 having an analytic distribution of 50%
        # After the aggregation, the result will be an analytic distribution of
        # ((1000 * 1) + (-100 * 0.5)) / (1000 - 100) = 1.055555556
        for grouping_key, base_line in base_line_map.items():
            total_factor = 0.0
            analytic_distribution_to_aggregate = defaultdict(float)
            for aggregated_base_line in aggregated_base_lines[grouping_key]:
                amount = aggregated_base_line['tax_details']['raw_total_excluded_currency']
                total_factor += amount
                for account_id, distribution in (aggregated_base_line['analytic_distribution'] or {}).items():
                    analytic_distribution_to_aggregate[account_id] += distribution * amount / 100.0
            analytic_distribution = {}
            for account_id, amount in analytic_distribution_to_aggregate.items():
                analytic_distribution[account_id] = amount * 100 / total_factor
            base_line['analytic_distribution'] = analytic_distribution

        return list(base_line_map.values())

    @api.model
    def _apply_base_lines_manual_amounts_to_reach(
        self,
        base_lines,
        company,
        target_base_amount_currency,
        target_base_amount,
        target_tax_amounts_mapping,
    ):
        """ Fix the tax amounts of the base lines passed as parameter by storing them in 'manual_tax_amounts' and make some
        adjustement to ensure the total of those lines will be exactly 'target_amount_currency'/'target_amount'.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        DEPRECATED: TO BE REMOVED IN MASTER

        :param base_lines:                  A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:                     The company owning the base lines.
        :param target_base_amount_currency: The expected base amount for the base lines expressed in foreign currency.
        :param target_base_amount:          The expected base amount for the base lines expressed in company currency.
        :param target_tax_amounts_mapping:   A mapping tax_id => dictionary containing:
            * tax_amount_currency:              The expected tax amount for the base lines expressed in foreign currency.
            * tax_amount:                       The expected tax amount for the base lines expressed in company currency.
        """
        currency = base_lines[0]['currency_id']

        # Smooth distribution of the delta base amount accross the base line, starting at the biggest one.
        sorted_base_lines = sorted(
            [
                base_line
                for base_line in base_lines
            ],
            key=lambda base_line: (bool(base_line['special_type']), -base_line['tax_details']['total_excluded_currency'])
        )
        base_lines_totals = self._compute_subset_base_lines_total(base_lines, company)
        for delta_suffix, delta_target_base_amount, delta_currency in (
            ('_currency', target_base_amount_currency, currency),
            ('', target_base_amount, company.currency_id),
        ):
            target_factors = [
                {
                    'factor': abs(
                        (base_line['tax_details']['total_excluded_currency'] + base_line['tax_details']['delta_total_excluded_currency'])
                        / base_lines_totals['base_amount_currency']
                    ),
                    'base_line': base_line,
                }
                for base_line in sorted_base_lines
            ]
            amounts_to_distribute = self._distribute_delta_amount_smoothly(
                precision_digits=delta_currency.decimal_places,
                delta_amount=delta_target_base_amount - base_lines_totals[f'base_amount{delta_suffix}'],
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                base_line = target_factor['base_line']
                tax_details = base_line['tax_details']
                taxes_data = tax_details['taxes_data']
                if delta_suffix == '_currency':
                    base_line['price_unit'] += amount_to_distribute / abs(base_line['quantity'] or 1.0)
                if not taxes_data:
                    continue

                first_batch = taxes_data[0]['batch']
                for tax_data in taxes_data:
                    tax = tax_data['tax']
                    if tax in first_batch:
                        tax_data[f'base_amount{delta_suffix}'] += amount_to_distribute
                    else:
                        break

        for tax_id_str, tax_amounts in target_tax_amounts_mapping.items():
            for delta_suffix, delta_target_tax_amount, delta_currency in (
                ('_currency', tax_amounts['tax_amount_currency'], currency),
                ('', tax_amounts['tax_amount'], company.currency_id),
            ):
                current_tax_amounts = base_lines_totals['tax_amounts_mapping'][tax_id_str]
                if not current_tax_amounts['tax_amount_currency']:
                    continue

                target_factors = [
                    {
                        'factor': abs(tax_data['tax_amount_currency'] / current_tax_amounts['tax_amount_currency']),
                        'tax_data': tax_data,
                    }
                    for base_line in sorted_base_lines
                    for tax_data in base_line['tax_details']['taxes_data']
                    if str(tax_data['tax'].id) == tax_id_str
                ]
                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=delta_currency.decimal_places,
                    delta_amount=delta_target_tax_amount - current_tax_amounts[f'tax_amount{delta_suffix}'],
                    target_factors=target_factors,
                )
                for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                    tax_data = target_factor['tax_data']
                    tax_data[f'tax_amount{delta_suffix}'] += amount_to_distribute

        self._fix_base_lines_tax_details_on_manual_tax_amounts(
            base_lines=base_lines,
            company=company,
        )

    @api.model
    def _reduce_base_lines_to_target_amount(
        self,
        base_lines,
        company,
        amount_type,
        amount,
        computation_key=None,
        grouping_function=None,
        aggregate_function=None,
    ):
        """

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company of the base lines.
        :param amount_type:         'fixed' or 'percent' indicating the type of the down payment.
        :param amount:              The amount of the down payment in case of 'fixed' amount_type. Otherwise, a percentage [0-100].
        :param computation_key:     The key that will be used to split the base lines to round the tax amounts.
        :param grouping_function:   An optional function taking a base line as parameter and returning a grouping key
                                    being the way the base lines will be aggregated all together.
                                    By default, the base lines will be aggregated by taxes.
        :param aggregate_function:  An optional function taking the 2 base lines as parameter to be aggregated together.
        :return:                    A new list of base lines having total amounts exactly matching the expected 'amount'/'amount_type'.
        """
        if not base_lines:
            return []

        currency = base_lines[0]['currency_id']
        rate = base_lines[0]['rate']

        # Compute the current total amount of the base lines.
        def grouping_function_total(base_line, tax_data):
            return True

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function_total)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        total_amount_currency = sum(
            values['total_excluded_currency'] + values['tax_amount_currency']
            for _grouping_key, values in values_per_grouping_key.items()
        )
        total_amount = sum(
            values['total_excluded'] + values['tax_amount']
            for _grouping_key, values in values_per_grouping_key.items()
        )

        # Compute the current total tax amount per tax.
        def grouping_function_tax(base_line, tax_data):
            return str(tax_data['tax'].id) if tax_data else None

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function_tax)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        tax_amounts_per_tax = {
            grouping_key: {
                'tax_amount_currency': values['tax_amount_currency'],
                'tax_amount': values['tax_amount'],
                'base_amount_currency': values['base_amount_currency'],
                'base_amount': values['base_amount'],
            }
            for grouping_key, values in values_per_grouping_key.items()
            if grouping_key
        }

        # Turn the 'amount_type' / 'amount' into a percentage and the total amounts to be reached
        # from the base lines.
        sign = -1 if amount < 0.0 else 1
        signed_amount = sign * amount
        if amount_type == 'fixed':
            percentage = (signed_amount / total_amount_currency) if total_amount_currency else 0.0
            expected_total_amount_currency = currency.round(amount)
            expected_total_amount = company.currency_id.round(expected_total_amount_currency / rate) if rate else 0.0
        else:  # if amount_type == 'percent':
            percentage = signed_amount / 100.0
            expected_total_amount_currency = currency.round(total_amount_currency * sign * percentage)
            expected_total_amount = company.currency_id.round(total_amount * sign * percentage)

        # Compute the expected amounts.
        expected_tax_amounts = {
            grouping_key: {
                'tax_amount_currency': currency.round(values['tax_amount_currency'] * sign * percentage),
                'tax_amount': company.currency_id.round(values['tax_amount'] * sign * percentage),
                'base_amount_currency': currency.round(values['base_amount_currency'] * sign * percentage),
                'base_amount': company.currency_id.round(values['base_amount'] * sign * percentage),
            }
            for grouping_key, values in tax_amounts_per_tax.items()
        }
        expected_base_amount_currency = expected_total_amount_currency - sum(
            values['tax_amount_currency']
            for values in expected_tax_amounts.values()
        )
        expected_base_amount = expected_total_amount - sum(
            values['tax_amount']
            for values in expected_tax_amounts.values()
        )

        # Reduce the base lines to minimize the number of lines.
        reduced_base_lines = self._reduce_base_lines_with_grouping_function(
            base_lines=base_lines,
            grouping_function=grouping_function,
            aggregate_function=aggregate_function,
            computation_key=computation_key,
        )
        if not reduced_base_lines:
            return []

        # Reduce the unit price to approach the target amount.
        new_base_lines = []
        for base_line in reduced_base_lines:
            new_base_lines.append(self._prepare_base_line_for_taxes_computation(
                base_line,
                price_unit=base_line['price_unit'] * sign * percentage,
                computation_key=computation_key,
            ))
        self._add_tax_details_in_base_lines(new_base_lines, company)
        self._round_base_lines_tax_details(new_base_lines, company)

        # Smooth distribution of the delta tax/base amounts.
        sorted_base_lines = sorted(
            new_base_lines,
            key=lambda base_line: (bool(base_line['special_type']), -base_line['tax_details']['total_excluded_currency'])
        )
        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(new_base_lines, grouping_function_tax)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        current_tax_amounts_per_tax = {
            grouping_key: {
                'tax_amount_currency': values['tax_amount_currency'],
                'tax_amount': values['tax_amount'],
                'base_amount_currency': values['base_amount_currency'],
                'base_amount': values['base_amount'],
            }
            for grouping_key, values in values_per_grouping_key.items()
            if grouping_key
        }
        for tax_id_str, tax_amounts in current_tax_amounts_per_tax.items():
            for delta_suffix, delta_tax_amount, delta_base_amount, delta_currency in (
                (
                    '_currency',
                    expected_tax_amounts[tax_id_str]['tax_amount_currency'] - tax_amounts['tax_amount_currency'],
                    expected_tax_amounts[tax_id_str]['base_amount_currency'] - tax_amounts['base_amount_currency'],
                    currency,
                ),
                (
                    '',
                    expected_tax_amounts[tax_id_str]['tax_amount'] - tax_amounts['tax_amount'],
                    expected_tax_amounts[tax_id_str]['base_amount'] - tax_amounts['base_amount'],
                    company.currency_id,
                ),
            ):
                # Tax amount.
                tax_amount_currency = tax_amounts['tax_amount_currency']
                if tax_amount_currency:
                    target_factors = [
                        {
                            'factor': abs(tax_data['tax_amount_currency'] / tax_amount_currency),
                            'base_line': base_line,
                            'tax_data': tax_data,
                        }
                        for base_line in sorted_base_lines
                        for tax_data in base_line['tax_details']['taxes_data']
                        if str(tax_data['tax'].id) == tax_id_str
                    ]
                    amounts_to_distribute = self._distribute_delta_amount_smoothly(
                        precision_digits=delta_currency.decimal_places,
                        delta_amount=delta_tax_amount,
                        target_factors=target_factors,
                    )
                    for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                        tax_data = target_factor['tax_data']
                        tax_data[f'tax_amount{delta_suffix}'] += amount_to_distribute

                # Base amount.
                base_amount_currency = tax_amounts['base_amount_currency']
                if base_amount_currency:
                    target_factors = [
                        {
                            'factor': abs(tax_data['base_amount_currency'] / base_amount_currency),
                            'base_line': base_line,
                            'tax_data': tax_data,
                        }
                        for base_line in sorted_base_lines
                        for tax_data in base_line['tax_details']['taxes_data']
                        if str(tax_data['tax'].id) == tax_id_str
                    ]
                    amounts_to_distribute = self._distribute_delta_amount_smoothly(
                        precision_digits=delta_currency.decimal_places,
                        delta_amount=delta_base_amount,
                        target_factors=target_factors,
                    )
                    for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                        tax_data = target_factor['tax_data']
                        tax_data[f'base_amount{delta_suffix}'] += amount_to_distribute

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(new_base_lines, grouping_function_total)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        current_base_amount_currency = sum(
            values['total_excluded_currency']
            for _grouping_key, values in values_per_grouping_key.items()
        )
        current_base_amount = sum(
            values['total_excluded']
            for _grouping_key, values in values_per_grouping_key.items()
        )
        for delta_suffix, delta_base_amount, delta_currency in (
            ('_currency', expected_base_amount_currency - current_base_amount_currency, currency),
            ('', expected_base_amount - current_base_amount, company.currency_id),
        ):
            target_factors = [
                {
                    'factor': abs(
                        (base_line['tax_details']['total_excluded_currency'] + base_line['tax_details']['delta_total_excluded_currency'])
                        / current_base_amount_currency
                    ) if current_base_amount_currency else 0.0,
                    'base_line': base_line,
                }
                for base_line in sorted_base_lines
            ]
            amounts_to_distribute = self._distribute_delta_amount_smoothly(
                precision_digits=delta_currency.decimal_places,
                delta_amount=delta_base_amount,
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                base_line = target_factor['base_line']
                tax_details = base_line['tax_details']
                tax_details[f'delta_total_excluded{delta_suffix}'] += amount_to_distribute
                if delta_suffix == '_currency':
                    base_line['price_unit'] += amount_to_distribute

        return new_base_lines

    @api.model
    def _partition_base_lines_taxes(self, base_lines, partition_function):
        """ Partition the taxes of base lines passed as parameter.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:              The base lines.
        :param partition_function:      A function taking <base_line, tax_data> as parameter and returning
                                        True if the tax has to be kept or not.
        :return:                        A tuple <base_lines_partition_taxes, has_taxes_to_exclude> where
            * base_lines_partition_taxes:   A list of tuple <base_line, taxes_to_keep, taxes_to_exclude>
            * has_taxes_to_exclude:         A boolean indicating if at least one tax to exclude has been found.
        """
        has_taxes_to_exclude = False
        base_lines_partition_taxes = []
        for base_line in base_lines:
            tax_details = base_line['tax_details']
            taxes_data = tax_details['taxes_data']
            taxes_to_keep = self.env['account.tax']
            taxes_to_exclude = self.env['account.tax']
            for tax_data in taxes_data:
                if partition_function(base_line, tax_data):
                    taxes_to_keep += tax_data['tax']
                else:
                    taxes_to_exclude += tax_data['tax']
            if taxes_to_exclude:
                has_taxes_to_exclude = True
            base_lines_partition_taxes.append((base_line, taxes_to_keep, taxes_to_exclude))
        return base_lines_partition_taxes, has_taxes_to_exclude

    @api.model
    def _prepare_discountable_base_lines(self, base_lines, company, exclude_function=None):
        """ Prepare base lines on which we can compute all kind of discount.
        This method remove all part of base lines / taxes that are not eligible for a discount.
        Those taxes are given by the '_can_be_discounted' method giving False if not discountable.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company of the base lines.
        :param exclude_function:    An optional function taking a base line and a tax_data as parameter and returning
                                    a boolean indicating if the tax_data has to be exclude from the computation.
        :return:                    The base lines that are discountable.
        """
        def dispatch_exclude_function(base_line, tax_data):
            return not tax_data['tax']._can_be_discounted() or (exclude_function and exclude_function(base_line, tax_data))

        return self._dispatch_taxes_into_new_base_lines(base_lines, company, dispatch_exclude_function)

    # -------------------------------------------------------------------------
    # GLOBAL DISCOUNT
    # -------------------------------------------------------------------------

    @api.model
    def _prepare_global_discount_lines(
        self,
        base_lines,
        company,
        amount_type,
        amount,
        computation_key='global_discount',
        grouping_function=None,
    ):
        """ Prepare negative lines to be added representing a global discount.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company of the base lines.
        :param amount_type:         'fixed' or 'percent' indicating the type of the discount.
        :param amount:              The amount to be discounted in case of 'fixed' amount_type. Otherwise, a percentage [0-100].
        :param computation_key:     The key that will be used to split the base lines to round the tax amounts.
        :param grouping_function:   An optional function taking a base line as parameter and returning a grouping key
                                    being the way the base lines will be aggregated all together.
                                    By default, the base lines will be aggregated by taxes.
        :return:                    The negative base lines representing the global discount.
        """
        discountable_base_lines = self._prepare_discountable_base_lines(base_lines, company)
        new_base_lines = self._reduce_base_lines_to_target_amount(
            base_lines=discountable_base_lines,
            company=company,
            amount_type=amount_type,
            amount=-amount,
            computation_key=computation_key,
            grouping_function=grouping_function,
        )
        self._fix_base_lines_tax_details_on_manual_tax_amounts(
            base_lines=new_base_lines,
            company=company,
        )
        return new_base_lines

    # -------------------------------------------------------------------------
    # DOWN PAYMENT
    # -------------------------------------------------------------------------

    @api.model
    def _prepare_base_lines_for_down_payment(
        self,
        base_lines,
        company,
        exclude_function=None,
    ):
        """ Prepare base lines on which we can compute down payments.
        This method wrap all part of base lines / taxes that are not eligible for a down payment into the base amount.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company of the base lines.
        :param exclude_function:    An optional function taking a base line and a tax_data as parameter and returning
                                    a boolean indicating if the tax_data has to be exclude from the computation.
        :return:                    The negative base lines representing the global discount.
        """
        def dispatch_exclude_function(base_line, tax_data):
            return not tax_data['tax']._can_be_discounted() or (exclude_function and exclude_function(base_line, tax_data))

        new_base_lines = self._dispatch_taxes_into_new_base_lines(base_lines, company, dispatch_exclude_function)
        return new_base_lines + self._turn_removed_taxes_into_new_base_lines(new_base_lines, company)

    @api.model
    def _prepare_down_payment_lines(
        self,
        base_lines,
        company,
        amount_type,
        amount,
        computation_key='down_payment',
        grouping_function=None,
    ):
        """ Prepare the base lines to be added representing a down payment.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company of the base lines.
        :param amount_type:         'fixed' or 'percent' indicating the type of the down payment.
        :param amount:              The amount of the down payment in case of 'fixed' amount_type. Otherwise, a percentage [0-100].
        :param computation_key:     The key that will be used to split the base lines to round the tax amounts.
        :param grouping_function:   An optional function taking a base line as parameter and returning a grouping key
                                    being the way the base lines will be aggregated all together.
                                    By default, the base lines will be aggregated by taxes.
        :return:                    The negative base lines representing the global discount.
        """
        base_lines_for_dp = self._prepare_base_lines_for_down_payment(base_lines, company)
        new_base_lines = self._reduce_base_lines_to_target_amount(
            base_lines=base_lines_for_dp,
            company=company,
            amount_type=amount_type,
            amount=amount,
            computation_key=computation_key,
            grouping_function=grouping_function,
        )
        self._fix_base_lines_tax_details_on_manual_tax_amounts(
            base_lines=new_base_lines,
            company=company,
        )
        return new_base_lines

    # -------------------------------------------------------------------------
    # DISPATCHING OF LINES
    # -------------------------------------------------------------------------

    @api.model
    def _dispatch_taxes_into_new_base_lines(self, base_lines, company, exclude_function):
        """ Extract taxes from base lines and turn them into sub-base lines.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company of the base lines.
        :param exclude_function:    A function taking a base line and a tax_data as parameter and returning
                                    a boolean indicating if the tax_data has to be exclude or not.
        :return:                    The new base lines with some extra data that have been removed.
                                    The newly created base lines will be under the 'removed_taxes_data_base_lines' key.
        """
        def partition_function(base_line, tax_data):
            return not exclude_function(base_line, tax_data)

        base_lines_partition_taxes = self._partition_base_lines_taxes(base_lines, partition_function)[0]
        new_base_lines_list = [[] for _base_line in base_lines]
        to_process = [
            (index, base_line, taxes_to_exclude)
            for index, (base_line, taxes_to_keep, taxes_to_exclude) in enumerate(base_lines_partition_taxes)
        ]
        while to_process:
            index, base_line, taxes_to_exclude = to_process[0]
            to_process = to_process[1:]

            tax_details = base_line['tax_details']
            taxes_data = tax_details['taxes_data']

            # Get the index of the next 'tax_data' to exclude.
            next_split_index = None
            for i, tax_data in enumerate(taxes_data):
                if tax_data['tax'] in taxes_to_exclude:
                    next_split_index = i
                    break

            if next_split_index is None:
                new_base_lines_list[index].append(dict(base_line))
                continue

            common_taxes_data = taxes_data[:next_split_index]
            tax_data_to_remove = taxes_data[next_split_index]
            remaining_taxes_data = taxes_data[next_split_index + 1:]

            # Split 'tax_details'.
            first_tax_details = {
                k: tax_details[k]
                for k in (
                    'raw_total_excluded_currency',
                    'raw_total_excluded',
                    'total_excluded_currency',
                    'total_excluded',
                    'delta_total_excluded_currency',
                    'delta_total_excluded',
                )
            }
            first_tax_details['taxes_data'] = common_taxes_data
            first_tax_details['raw_total_included_currency'] = (
                first_tax_details['raw_total_excluded_currency']
                + sum(common_tax_data['raw_tax_amount_currency'] for common_tax_data in common_taxes_data)
            )
            first_tax_details['total_included_currency'] = (
                first_tax_details['total_excluded_currency']
                + first_tax_details['delta_total_excluded_currency']
                + sum(common_tax_data['tax_amount_currency'] for common_tax_data in common_taxes_data)
            )
            first_tax_details['raw_total_included'] = (
                first_tax_details['raw_total_excluded']
                + sum(common_tax_data['raw_tax_amount'] for common_tax_data in common_taxes_data)
            )
            first_tax_details['total_included'] = (
                first_tax_details['total_excluded']
                + first_tax_details['delta_total_excluded']
                + sum(common_tax_data['tax_amount'] for common_tax_data in common_taxes_data)
            )
            second_tax_details = {
                'raw_total_excluded_currency': tax_data_to_remove['raw_tax_amount_currency'],
                'raw_total_excluded': tax_data_to_remove['raw_tax_amount'],
                'total_excluded_currency': tax_data_to_remove['tax_amount_currency'],
                'total_excluded': tax_data_to_remove['tax_amount'],
                'delta_total_excluded_currency': 0.0,
                'delta_total_excluded': 0.0,
                'raw_total_included_currency': tax_data_to_remove['raw_tax_amount_currency'],
                'raw_total_included': tax_data_to_remove['raw_tax_amount'],
                'total_included_currency': tax_data_to_remove['tax_amount_currency'],
                'total_included': tax_data_to_remove['tax_amount'],
                'taxes_data': [],
            }

            target_factors = [
                {
                    'factor': first_tax_details['raw_total_excluded_currency'],
                    'tax_details': first_tax_details,
                },
                {
                    'factor': second_tax_details['raw_total_excluded_currency'],
                    'tax_details': second_tax_details,
                },
            ]
            for remaining_tax_data in remaining_taxes_data:
                if remaining_tax_data['tax'] in tax_data_to_remove['taxes']:
                    new_remaining_taxes_data = self._split_tax_data(base_line, remaining_tax_data, company, target_factors)

                    first_tax_data = new_remaining_taxes_data[0]

                    second_tax_details['taxes_data'].append(new_remaining_taxes_data[1])
                    second_tax_details['raw_total_included_currency'] += new_remaining_taxes_data[1]['raw_tax_amount_currency']
                    second_tax_details['raw_total_included'] += new_remaining_taxes_data[1]['raw_tax_amount']
                    second_tax_details['total_included_currency'] += new_remaining_taxes_data[1]['tax_amount_currency']
                    second_tax_details['total_included'] += new_remaining_taxes_data[1]['tax_amount']
                else:
                    first_tax_data = remaining_tax_data

                first_tax_details['taxes_data'].append(first_tax_data)
                first_tax_details['raw_total_included_currency'] += first_tax_data['raw_tax_amount_currency']
                first_tax_details['raw_total_included'] += first_tax_data['raw_tax_amount']
                first_tax_details['total_included_currency'] += first_tax_data['tax_amount_currency']
                first_tax_details['total_included'] += first_tax_data['tax_amount']

            # Split 'base_line'.
            first_taxes = self.env['account.tax']
            for tax_data in first_tax_details['taxes_data']:
                first_taxes += tax_data['tax']
            first_base_line = self._prepare_base_line_for_taxes_computation(
                base_line,
                tax_ids=first_taxes,
                tax_details=first_tax_details,
            )

            second_taxes = self.env['account.tax']
            for tax_data in second_tax_details['taxes_data']:
                second_taxes += tax_data['tax']
            second_base_line = self._prepare_base_line_for_taxes_computation(
                base_line,
                tax_ids=second_taxes,
                price_unit=(
                    second_tax_details['raw_total_excluded_currency']
                    + sum(
                        sub_tax_data['raw_tax_amount_currency']
                        for sub_tax_data in second_tax_details['taxes_data']
                        if sub_tax_data['tax'].price_include
                    )
                ) / (base_line['quantity'] or 1.0),
                tax_details=second_tax_details,
                _removed_tax_data=tax_data_to_remove,
            )
            to_process = [
                (index, first_base_line, taxes_to_exclude),
                (index, second_base_line, taxes_to_exclude),
            ] + to_process

        final_base_lines = []
        for new_base_lines in new_base_lines_list:
            new_base_lines[0]['removed_taxes_data_base_lines'] = new_base_lines[1:]
            final_base_lines.append(new_base_lines[0])
        return final_base_lines

    @api.model
    def _turn_removed_taxes_into_new_base_lines(self, base_lines, company, grouping_function=None, aggregate_function=None):
        """ Merge the sub 'removed_taxes_data_base_lines' generated by '_dispatch_taxes_into_new_base_lines'
        into the parent line.

        [!] Only added python-side.

        :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:             The company owning the base lines.
        :param grouping_function:   An optional function taking a base line as parameter and returning a grouping key
                                    being the way the base lines will be aggregated all together.
                                    By default, the base lines will be aggregated by taxes.
        :param aggregate_function:  An optional function taking the 2 base lines as parameter to be aggregated together.
        """
        extra_base_lines = []
        for base_line in base_lines:
            extra_base_lines += base_line['removed_taxes_data_base_lines']
        return self._reduce_base_lines_with_grouping_function(
            base_lines=extra_base_lines,
            grouping_function=grouping_function,
            aggregate_function=aggregate_function,
        )

    @api.model
    def _dispatch_global_discount_lines(self, base_lines, company):
        """ Dispatch the global discount lines present inside the base_lines passed as parameter across the others under the
        'discount_base_lines' key.

        [!] Only added python-side.

        :param base_lines:  A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:     The company owning the base lines.
        :return:            New base lines without any global discount but sub-lines added under the 'discount_base_lines' key.
        """
        # Dispatch lines.
        # First, we need to distinguish the mapping between the global discount lines and the others.
        # For now, we only dispatch base on taxes.
        new_base_lines = []
        discount_data_per_taxes = {}
        dispatched_neg_base_lines = []
        for base_line in base_lines:
            tax_details = base_line['tax_details']
            taxes_data = tax_details['taxes_data']

            # Get all the taxes flattened.
            taxes = self.env['account.tax']
            for gb_tax_data in taxes_data:
                taxes += gb_tax_data['tax']
            taxes = taxes.filtered(lambda tax: tax._can_be_discounted())

            discount_data = discount_data_per_taxes.setdefault(taxes, {
                'base_lines': [],
                'discount_base_lines': [],
            })

            new_base_line = {
                **base_line,
                'discount_base_lines': [],
            }

            if base_line['special_type'] == 'global_discount':
                discount_data['discount_base_lines'].append(new_base_line)
            else:
                discount_data['base_lines'].append(new_base_line)
            new_base_lines.append(new_base_line)

        # Split the discount base line accross the others.
        for discount_data in discount_data_per_taxes.values():
            discount_data['target_factors'] = [
                {
                    'base_line': base_line,
                    'factor': base_line['tax_details']['raw_total_excluded_currency'],
                }
                for base_line in discount_data['base_lines']
            ]
            if discount_data['target_factors']:
                dispatched_neg_base_lines += discount_data['discount_base_lines']
            else:
                continue

            for discount_base_line in discount_data['discount_base_lines']:
                splitted_base_lines = self._split_base_line(
                    base_line=discount_base_line,
                    company=company,
                    target_factors=discount_data['target_factors'],
                )
                for base_line, new_base_line in zip(discount_data['base_lines'], splitted_base_lines):
                    base_line['discount_base_lines'].append(new_base_line)
        return [x for x in new_base_lines if x not in dispatched_neg_base_lines]

    @api.model
    def _squash_global_discount_lines(self, base_lines, company):
        """ Merge the sub global discount base lines generated by '_dispatch_global_discount_lines'
        into the parent line.

        [!] Only added python-side.

        :param base_lines:  A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:     The company owning the base lines.
        """
        for base_line in base_lines:
            for sub_base_line in base_line['discount_base_lines']:
                base_line['tax_details'] = self._merge_tax_details(
                    tax_details_1=base_line['tax_details'],
                    tax_details_2=sub_base_line['tax_details'],
                )

        self._fix_base_lines_tax_details_on_manual_tax_amounts(
            base_lines=[base_line for base_line in base_lines if base_line['discount_base_lines']],
            company=company,
        )

    @api.model
    def _dispatch_return_of_merchandise_lines(self, base_lines, company):
        """ Dispatch the return of merchandise lines present inside the base_lines passed as parameter across the others under the
        'return_of_merchandise_base_lines' key.
        What we call a return of merchandise is when the negative line matches exactly the parent line but has a negative quantity.
        So if you have 2 base lines, one with a quantity of 3 and the other with a quantity of -1, this method tries to reduce the
        quantity instead of considering the negative lines as a discount.

        [!] Only added python-side.

        :param base_lines:  A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:     The company owning the base lines.
        :return:            New base lines without any return of merchandise but sub-lines added under the 'return_of_merchandise_base_lines' key.
        """
        new_base_lines = []
        mapping = defaultdict(lambda: {
            '+': [],
            '-': [],
        })
        dispatched_neg_base_lines = []
        for base_line in base_lines:
            new_base_line = {
                **base_line,
                'return_of_merchandise_base_lines': [],
            }
            new_base_lines.append(new_base_line)

            if not base_line['product_id'] or base_line['quantity'] == 0.0:
                continue

            key = frozendict({
                'tax_ids': base_line['tax_ids'].ids,
                'product': base_line['product_id'].id,
                'price_unit': base_line['price_unit'],
                'discount': base_line['discount'],
            })

            is_negative = base_line['tax_details']['raw_total_excluded_currency'] < 0.0
            mapping[key]['-' if is_negative else '+'].append(new_base_line)

        for signed_base_lines in mapping.values():
            plus_base_lines = sorted(signed_base_lines['+'], key=lambda base_line: -base_line['quantity'])
            iter_plus_base_lines = iter(plus_base_lines)
            neg_base_lines = sorted(signed_base_lines['-'], key=lambda base_line: base_line['quantity'])
            iter_neg_base_lines = iter(neg_base_lines)
            plus_base_line = None
            plus_base_line_quantity = None
            neg_base_line = None
            neg_base_line_quantity = None
            target_factors_per_neg_base_line = []
            target_factors = None
            while True:

                if not neg_base_line or not neg_base_line_quantity:
                    neg_base_line = next(iter_neg_base_lines, None)
                    if neg_base_line:
                        neg_base_line_quantity = abs(neg_base_line['quantity'])
                        target_factors = []
                        target_factors_per_neg_base_line.append(target_factors)
                    else:
                        break

                if not plus_base_line or not plus_base_line_quantity:
                    plus_base_line = next(iter_plus_base_lines, None)
                    if plus_base_line:
                        plus_base_line_quantity = abs(plus_base_line['quantity'])
                    else:
                        break

                quantity_to_dispatch = min(neg_base_line_quantity, plus_base_line_quantity)
                target_factors.append({
                    'factor': quantity_to_dispatch / abs(neg_base_line['quantity']),
                    'quantity_to_dispatch': quantity_to_dispatch,
                    'plus_base_line': plus_base_line,
                    'quantity': -quantity_to_dispatch,
                })
                plus_base_line_quantity -= quantity_to_dispatch
                neg_base_line_quantity -= quantity_to_dispatch

            def populate_function(base_line, target_factor, kwargs):
                kwargs['price_unit'] = base_line['price_unit']
                kwargs['quantity'] = -target_factor['quantity_to_dispatch']

            for target_factors, neg_base_line in zip(target_factors_per_neg_base_line, neg_base_lines):
                if not target_factors:
                    continue

                dispatched_neg_base_lines.append(neg_base_line)
                splitted_base_lines = self._split_base_line(
                    base_line=neg_base_line,
                    company=company,
                    target_factors=target_factors,
                    populate_function=populate_function,
                )
                for target_factor, new_base_line in zip(target_factors, splitted_base_lines):
                    target_factor['plus_base_line']['return_of_merchandise_base_lines'].append(new_base_line)

        return [x for x in new_base_lines if x not in dispatched_neg_base_lines]

    @api.model
    def _squash_return_of_merchandise_lines(self, base_lines, company):
        """ Merge the sub return of merchandise base lines generated by '_dispatch_return_of_merchandise_lines'
        into the parent line.

        [!] Only added python-side.

        :param base_lines:  A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
        :param company:     The company owning the base lines.
        """
        for base_line in base_lines:
            for sub_base_line in base_line['return_of_merchandise_base_lines']:
                base_line['tax_details'] = self._merge_tax_details(
                    tax_details_1=base_line['tax_details'],
                    tax_details_2=sub_base_line['tax_details'],
                )
                base_line['quantity'] += sub_base_line['quantity']

        self._fix_base_lines_tax_details_on_manual_tax_amounts(
            base_lines=[base_line for base_line in base_lines if base_line['return_of_merchandise_base_lines']],
            company=company,
        )

    # -------------------------------------------------------------------------
    # EDI HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_delta_amount_to_reach_target(
        self,
        target_amount,
        target_currency,
        raw_current_amount,
        raw_current_amount_precision_digits,
    ):
        """ Get the minimum missing amount having 'raw_current_amount_precision_digits' as precision
        to be added to 'raw_current_amount' to give 'target_amount' after rounding using 'target_currency'.

        :param target_amount:                       The amount to reach after rounding the raw amount using 'target_currency'.
        :param target_currency:                     The currency used to round 'target_amount'.
        :param raw_current_amount:                  The raw amount that needs to reach 'target_amount'.
        :param raw_current_amount_precision_digits: The precision of the delta returned by this method.
        :return:
            Suppose 'raw_current_amount' is expressed with 'raw_current_amount_precision_digits'.
            Then, the delta returned by this method will be expressed with 'raw_current_amount_precision_digits'
            such as target_currency.round(raw_current_amount + delta) == target_amount
        """
        target_amount_sign = -1 if target_amount < 0.0 else 1
        raw_current_amount_rounding = math.pow(10, -raw_current_amount_precision_digits)
        tolerance_bounds = (
            float_round(
                abs(target_amount) + (target_currency.rounding / 2) - raw_current_amount_rounding,
                precision_digits=raw_current_amount_precision_digits,
            ),
            float_round(
                abs(target_amount) - (target_currency.rounding / 2),
                precision_digits=raw_current_amount_precision_digits,
            ),
        )

        signed_raw_current_amount = target_amount_sign * raw_current_amount
        if signed_raw_current_amount > tolerance_bounds[0]:
            delta_raw_amount = tolerance_bounds[0] - signed_raw_current_amount
        elif signed_raw_current_amount < tolerance_bounds[1]:
            delta_raw_amount = tolerance_bounds[1] - signed_raw_current_amount
        else:
            return 0.0

        return target_amount_sign * delta_raw_amount

    @api.model
    def _round_raw_total_excluded(
        self,
        base_lines,
        company,
        precision_digits=6,
        apply_strict_tolerance=False,
        in_foreign_currency=True,
    ):
        """ Round 'raw_total_excluded[_currency]' according 'precision_digits'.

        :param base_lines:              A list of python dictionaries created using the '_prepare_base_line_for_taxes_computation' method.
        :param company:                 The company owning the base lines.
        :param precision_digits:        The precision to be used to round.
        :param apply_strict_tolerance:  A flag ensuring a strict equality between rounded and raw amounts such as
                                            ROUND(SUM(raw_total_excluded FOREACH base_line), precision_digits)
                                            and SUM(total_excluded FOREACH base_line)
                                        If specified, the difference will be spread into the raw amounts to satisfy the equality.
        :param in_foreign_currency:     True if to be applied on amounts expressed in foreign currency,
                                        False for amounts expressed in company currency.
        """
        if not base_lines:
            return

        suffix_currency = base_lines[0]['currency_id'] if in_foreign_currency else company.currency_id
        suffix = '_currency' if in_foreign_currency else ''
        raw_field = f'raw_total_excluded{suffix}'

        for base_line in base_lines:
            tax_details = base_line['tax_details']
            tax_details[raw_field] = float_round(tax_details[raw_field], precision_digits=precision_digits)

        # Tolerance.
        if not apply_strict_tolerance:
            return

        def grouping_function(base_line, tax_data):
            return True

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        expected_total_excluded = sum(
            values[f'total_excluded{suffix}']
            for values in values_per_grouping_key.values()
        )
        current_raw_total_excluded = sum(
            base_line['tax_details'][raw_field]
            for base_line in base_lines
        )

        delta_raw_amount = self._get_delta_amount_to_reach_target(
            target_amount=expected_total_excluded,
            target_currency=suffix_currency,
            raw_current_amount=current_raw_total_excluded,
            raw_current_amount_precision_digits=precision_digits,
        )
        target_factors = [
            {
                'factor': base_line['tax_details'][raw_field],
                'base_line': base_line,
            }
            for base_line in base_lines
        ]
        amounts_to_distribute = self._distribute_delta_amount_smoothly(
            precision_digits=precision_digits,
            delta_amount=delta_raw_amount,
            target_factors=target_factors,
        )
        for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
            base_line = target_factor['base_line']
            base_line['tax_details'][raw_field] += amount_to_distribute

    @api.model
    def _add_and_round_raw_gross_total_excluded_and_discount(
        self,
        base_lines,
        company,
        precision_digits=6,
        apply_strict_tolerance=False,
        in_foreign_currency=True,
        account_discount_base_lines=False,
    ):
        """ Compute and add 'raw_gross_total_excluded[_currency]' / 'raw_gross_price_unit[_currency]' / 'raw_discount_amount[_currency]'
        to the tax details according 'precision_digits' / 'in_foreign_currency'.

        :param base_lines:                  A list of python dictionaries created using the '_prepare_base_line_for_taxes_computation' method.
        :param company:                     The company owning the base lines.
        :param precision_digits:            The precision to be used to round.
        :param apply_strict_tolerance:      A flag ensuring a strict equality between rounded and raw amounts such as
                                                ROUND(SUM(raw_total_excluded + raw_discount_amount FOREACH base_line), precision_digits)
                                                and SUM(total_excluded FOREACH base_line) + ROUND(SUM(raw_discount_amount FOREACH base_line))
                                            If specified, the difference will be spread into the 'raw_gross_total_excluded' to satisfy the
                                            equality.
        :param in_foreign_currency:         True if to be applied on amounts expressed in foreign currency,
                                            False for amounts expressed in company currency.
        :param account_discount_base_lines: Account the distributed global discount in 'discount_base_lines'
                                            using '_dispatch_global_discount_lines' in 'raw_discount_amount'.
        """
        if not base_lines:
            return

        suffix_currency = base_lines[0]['currency_id'] if in_foreign_currency else company.currency_id
        suffix = '_currency' if in_foreign_currency else ''
        raw_field = f'raw_total_excluded{suffix}'

        for base_line in base_lines:
            tax_details = base_line['tax_details']
            raw_total_excluded = tax_details[raw_field]

            discount_factor = 1 - (base_line['discount'] / 100.0)
            if discount_factor:
                raw_gross_total_excluded = raw_total_excluded / discount_factor
            elif suffix == '_currency':
                raw_gross_total_excluded = base_line['price_unit'] * base_line['quantity']
            elif base_line['rate']:
                raw_gross_total_excluded = base_line['price_unit'] * base_line['quantity'] / base_line['rate']
            else:
                raw_gross_total_excluded = 0.0
            if account_discount_base_lines:
                raw_gross_total_excluded -= sum(
                    discount_base_line['tax_details'][raw_field]
                    for discount_base_line in base_line.get('discount_base_lines', [])
                )
            tax_details[f'raw_gross_total_excluded{suffix}'] = float_round(raw_gross_total_excluded, precision_digits=precision_digits)

            # Same as before but per unit.
            if float_is_zero(raw_gross_total_excluded, precision_digits=precision_digits):
                raw_gross_price_unit = base_line['price_unit']
                if not suffix:
                    if base_line['rate']:
                        raw_gross_price_unit /= base_line['rate']
                    else:
                        raw_gross_price_unit = 0.0
            elif not base_line['quantity']:
                raw_gross_price_unit = raw_gross_total_excluded
            else:
                raw_gross_price_unit = raw_gross_total_excluded / base_line['quantity']
            tax_details[f'raw_gross_price_unit{suffix}'] = float_round(raw_gross_price_unit, precision_digits=precision_digits)

            # Compute the amount of the discount due to the 'discount' value set on 'base_line'.
            raw_discount_amount = raw_gross_total_excluded - raw_total_excluded
            tax_details[f'raw_discount_amount{suffix}'] = float_round(raw_discount_amount, precision_digits=precision_digits)

        # Tolerance.
        if not apply_strict_tolerance:
            return

        def grouping_function(base_line, tax_data):
            return True

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        expected_total_excluded = sum(
            values[f'total_excluded{suffix}']
            for values in values_per_grouping_key.values()
        )
        raw_total_discount_amount = sum(
            base_line['tax_details'][f'raw_discount_amount{suffix}']
            for values in values_per_grouping_key.values()
            for base_line, _taxes_data in values['base_line_x_taxes_data']
        )
        raw_total_gross_amount = sum(
            base_line['tax_details'][f'raw_gross_total_excluded{suffix}']
            for values in values_per_grouping_key.values()
            for base_line, _taxes_data in values['base_line_x_taxes_data']
        )
        total_discount_amount = suffix_currency.round(raw_total_discount_amount)
        expected_total_gross_amount = expected_total_excluded + total_discount_amount

        delta_raw_amount = self._get_delta_amount_to_reach_target(
            target_amount=expected_total_gross_amount,
            target_currency=suffix_currency,
            raw_current_amount=raw_total_gross_amount,
            raw_current_amount_precision_digits=precision_digits,
        )
        target_factors = [
            {
                'factor': base_line['tax_details'][f'raw_total_excluded{suffix}'],
                'base_line': base_line,
            }
            for values in values_per_grouping_key.values()
            for base_line, _taxes_data in values['base_line_x_taxes_data']
        ]
        amounts_to_distribute = self._distribute_delta_amount_smoothly(
            precision_digits=precision_digits,
            delta_amount=delta_raw_amount,
            target_factors=target_factors,
        )
        for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
            base_line = target_factor['base_line']
            base_line['tax_details'][f'raw_gross_total_excluded{suffix}'] += amount_to_distribute

    @api.model
    def _round_raw_gross_total_excluded_and_discount(
        self,
        base_lines,
        company,
        in_foreign_currency=True,
    ):
        if not base_lines:
            return

        suffix_currency = base_lines[0]['currency_id'] if in_foreign_currency else company.currency_id
        suffix = '_currency' if in_foreign_currency else ''

        # Raw rounding.
        current_gross_total_excluded = 0.0
        current_discount_amount = 0.0
        current_raw_discount_amount = 0.0
        for base_line in base_lines:
            tax_details = base_line['tax_details']
            gross_total_excluded = tax_details[f'gross_total_excluded{suffix}'] = float_round(
                value=tax_details[f'raw_gross_total_excluded{suffix}'],
                precision_rounding=suffix_currency.rounding,
            )
            current_gross_total_excluded += gross_total_excluded

            raw_discount_amount = tax_details[f'raw_discount_amount{suffix}']
            discount_amount = tax_details[f'discount_amount{suffix}'] = float_round(
                value=raw_discount_amount,
                precision_rounding=suffix_currency.rounding,
            )
            current_discount_amount += discount_amount
            current_raw_discount_amount += raw_discount_amount

        # Collect the 'total_excluded'.
        def grouping_function(base_line, tax_data):
            return True

        base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        expected_total_excluded = sum(
            values[f'total_excluded{suffix}']
            for values in values_per_grouping_key.values()
        )

        # Fix rounding issues for 'gross_total_excluded'.
        # Note: 'expected_gross_total_excluded' contains also the 'delta_total_excluded' to put all the difference due to the
        # global taxes rounding on it instead of putting it on 'discount_amount' since the discount won't always be there.
        expected_gross_total_excluded = expected_total_excluded + float_round(
            value=current_raw_discount_amount,
            precision_rounding=suffix_currency.rounding,
        )

        target_factors = [
            {
                'factor': 1.0,  # By default, we avoid to have more than one cent as a difference per line.
                'base_line': base_line,
            }
            for base_line in base_lines
        ]
        amounts_to_distribute = self._distribute_delta_amount_smoothly(
            precision_digits=suffix_currency.decimal_places,
            delta_amount=expected_gross_total_excluded - current_gross_total_excluded,
            target_factors=target_factors,
        )
        for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
            base_line = target_factor['base_line']
            base_line['tax_details'][f'gross_total_excluded{suffix}'] += amount_to_distribute

        # Fix rounding issues for 'discount_amount'.
        expected_discount_amount = expected_gross_total_excluded - expected_total_excluded
        amounts_to_distribute = self._distribute_delta_amount_smoothly(
            precision_digits=suffix_currency.decimal_places,
            delta_amount=expected_discount_amount - current_discount_amount,
            target_factors=target_factors,
        )
        for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
            base_line = target_factor['base_line']
            base_line['tax_details'][f'discount_amount{suffix}'] += amount_to_distribute

    @api.model
    def _round_raw_tax_amounts(
        self,
        base_lines_aggregated_values,
        company,
        precision_digits=6,
        apply_strict_tolerance=False,
        in_foreign_currency=True,
    ):
        """ Round 'raw_tax_amount[_currency]'/'raw_base_amount[_currency]' according 'precision_digits' / 'in_foreign_currency'.

        :param base_lines_aggregated_values:    The result of '_aggregate_base_lines_tax_details'.
        :param company:                         The company owning the base lines.
        :param precision_digits:                The precision to be used to round.
        :param apply_strict_tolerance:          A flag ensuring a strict equality between rounded and raw amounts such as
                                                    ROUND(SUM(raw_tax_amount FOREACH base_line), precision_digits)
                                                    and SUM(tax_amount FOREACH base_line)
                                                If specified, the difference will be spread into the raw amounts to satisfy the equality.
                                                Regarding the base amounts, we keep a consistency between the tax rate between
                                                each raw_base_amount and raw_tax_amount but also globally with rounded amounts.
        :param in_foreign_currency:             True if to be applied on amounts expressed in foreign currency,
                                                False for amounts expressed in company currency.
        """
        if not base_lines_aggregated_values:
            return

        suffix_currency = base_lines_aggregated_values[0][0]['currency_id'] if in_foreign_currency else company.currency_id
        suffix = '_currency' if in_foreign_currency else ''

        for _base_line, aggregated_values in base_lines_aggregated_values:
            for values in aggregated_values.values():
                values[f'raw_tax_amount{suffix}'] = float_round(values[f'raw_tax_amount{suffix}'], precision_digits=precision_digits)
                values[f'raw_base_amount{suffix}'] = float_round(values[f'raw_base_amount{suffix}'], precision_digits=precision_digits)

        # Tolerance.
        if not apply_strict_tolerance:
            return

        tax_field = f'tax_amount{suffix}'
        raw_tax_field = f'raw_{tax_field}'
        base_field = f'base_amount{suffix}'
        raw_base_field = f'raw_{base_field}'
        values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        for grouping_key, values in values_per_grouping_key.items():
            tax_rate = (values[raw_tax_field] / values[raw_base_field]) if values[raw_base_field] else 0.0

            target_factors = [
                {
                    'factor': aggregated_values[grouping_key][raw_tax_field],
                    'aggregated_values': aggregated_values[grouping_key],
                }
                for base_line, aggregated_values in base_lines_aggregated_values
                if grouping_key in aggregated_values
            ]

            # Tax amount.
            expected_tax_amount = values[tax_field]
            current_raw_tax_amount = values[raw_tax_field]
            delta_raw_amount = self._get_delta_amount_to_reach_target(
                target_amount=expected_tax_amount,
                target_currency=suffix_currency,
                raw_current_amount=current_raw_tax_amount,
                raw_current_amount_precision_digits=precision_digits,
            )
            amounts_to_distribute = self._distribute_delta_amount_smoothly(
                precision_digits=precision_digits,
                delta_amount=delta_raw_amount,
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                aggregated_values = target_factor['aggregated_values']
                aggregated_values[raw_tax_field] += amount_to_distribute
                values[raw_tax_field] += amount_to_distribute
                if amount_to_distribute and tax_rate:
                    new_raw_base_amount = aggregated_values[raw_tax_field] / tax_rate
                    rounded_new_raw_base_amount = float_round(new_raw_base_amount, precision_digits=precision_digits)
                    values[raw_base_field] += rounded_new_raw_base_amount - aggregated_values[raw_base_field]
                    aggregated_values[raw_base_field] = rounded_new_raw_base_amount

            # Base amount.
            if tax_rate:
                current_tax_raw_base_amount = (current_raw_tax_amount + delta_raw_amount) / tax_rate
                delta_raw_amount = self._get_delta_amount_to_reach_target(
                    target_amount=current_tax_raw_base_amount,
                    target_currency=suffix_currency,
                    raw_current_amount=values[raw_base_field],
                    raw_current_amount_precision_digits=precision_digits,
                )
                amounts_to_distribute = self._distribute_delta_amount_smoothly(
                    precision_digits=precision_digits,
                    delta_amount=delta_raw_amount,
                    target_factors=target_factors,
                )
                for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                    aggregated_values = target_factor['aggregated_values']
                    aggregated_values[raw_base_field] += amount_to_distribute
                    values[raw_base_field] += amount_to_distribute

    # -------------------------------------------------------------------------
    # END HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js)
    # -------------------------------------------------------------------------

    def flatten_taxes_hierarchy(self):
        return self._flatten_taxes_and_sort_them()[0]

    def get_tax_tags(self, is_refund, repartition_type):
        document_type = 'refund' if is_refund else 'invoice'
        return self.repartition_line_ids\
            .filtered(lambda x: x.repartition_type == repartition_type and x.document_type == document_type)\
            .mapped('tag_ids')

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True, include_caba_tags=False, rounding_method=None):
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
        )
        self._add_tax_details_in_base_line(base_line, company, rounding_method=rounding_method)
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
                    'price_include': tax.price_include,
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

    def _filter_taxes_by_company(self, company_id):
        """ Filter taxes by the given company
            It goes through the company hierarchy until a tax is found
        """
        if not self:
            return self
        taxes, company = self.env['account.tax'], company_id
        while not taxes and company:
            taxes = self.filtered(lambda t: t.company_id == company)
            company = company.sudo().parent_id
        return taxes

    @api.model
    def _fix_tax_included_price(self, price, prod_taxes, line_taxes):
        """Subtract tax amount from price when corresponding "price included" taxes do not apply"""
        # FIXME get currency in param?
        prod_taxes = prod_taxes._origin
        line_taxes = line_taxes._origin
        incl_tax = prod_taxes.filtered(lambda tax: tax not in line_taxes and tax.price_include)
        if incl_tax:
            return incl_tax.compute_all(price)['total_excluded']
        return price

    @api.model
    def _fix_tax_included_price_company(self, price, prod_taxes, line_taxes, company_id):
        if company_id:
            #To keep the same behavior as in _compute_tax_id
            prod_taxes = prod_taxes.filtered(lambda tax: tax.company_id == company_id)
            line_taxes = line_taxes.filtered(lambda tax: tax.company_id == company_id)
        return self._fix_tax_included_price(price, prod_taxes, line_taxes)

    def _get_description_plaintext(self):
        self.ensure_one()
        if is_html_empty(self.description):
            return ''
        return html2plaintext(self.description)


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
    factor = fields.Float(string="Factor Ratio", compute="_compute_factor", help="Factor to apply on the account move lines generated from this distribution line")
    repartition_type = fields.Selection(string="Based On", selection=[('base', 'Base'), ('tax', 'of tax')], required=True, default='tax', help="Base on which the factor will be applied.")
    document_type = fields.Selection(string="Related to", selection=[('invoice', 'Invoice'), ('refund', 'Refund')], required=True)
    account_id = fields.Many2one(string="Account",
        comodel_name='account.account',
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'off_balance'))]",
        check_company=True,
        help="Account on which to post the tax amount")
    tag_ids = fields.Many2many(string="Tax Grids", comodel_name='account.account.tag', domain=[('applicability', '=', 'taxes')], copy=True, ondelete='restrict')
    tax_id = fields.Many2one(comodel_name='account.tax', index='btree_not_null', ondelete='cascade', check_company=True)
    company_id = fields.Many2one(string="Company", comodel_name='res.company', related="tax_id.company_id", store=True, help="The company this distribution line belongs to.")
    sequence = fields.Integer(string="Sequence", default=1,
        help="The order in which distribution lines are displayed and matched. For refunds to work properly, invoice distribution lines should be arranged in the same order as the credit note distribution lines they correspond to.")
    use_in_tax_closing = fields.Boolean(
        string="Tax Closing Entry",
        compute='_compute_use_in_tax_closing', store=True, readonly=False, precompute=True,
    )

    tag_ids_domain = fields.Binary(string="tag domain", help="Dynamic domain used for the tag that can be set on tax", compute="_compute_tag_ids_domain")

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
