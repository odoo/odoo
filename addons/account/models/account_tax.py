# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.tools import frozendict, groupby, split_every
from odoo.tools.float_utils import float_round
from odoo.tools.misc import clean_context, formatLang
from odoo.tools.translate import html_translate

from collections import defaultdict
from markupsafe import Markup

import ast
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

    @api.model
    def _check_misconfigured_tax_groups(self, company, countries):
        """ Searches the tax groups used on the taxes from company in countries that don't have
        at least a tax payable account, a tax receivable account or an advance tax payment account.

        :return: A boolean telling whether or not there are misconfigured groups for any
                 of these countries, in this company
        """
        return bool(self.env['account.tax'].search([
            *self.env['account.tax']._check_company_domain(company),
            ('country_id', 'in', countries.ids),
            '|',
            ('tax_group_id.tax_payable_account_id', '=', False),
            ('tax_group_id.tax_receivable_account_id', '=', False),
        ], limit=1))


class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = ['mail.thread']
    _description = 'Tax'
    _order = 'sequence,id'
    _check_company_auto = True
    _rec_names_search = ['name', 'description', 'invoice_label']
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(string='Tax Name', required=True, translate=True, tracking=True)
    name_searchable = fields.Char(store=False, search='_search_name',
          help="This dummy field lets us use another search method on the field 'name'."
               "This allows more freedom on how to search the 'name' compared to 'filter_domain'."
               "See '_search_name' and '_parse_name_search' for why this is not possible with 'filter_domain'.")
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
        domain="[('deprecated', '=', False)]",
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
    invoice_legal_notes = fields.Html(string="Legal Notes", help="Legal mentions that have to be printed on the invoices.")

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
            if duplicates := self.search(expression.OR(domains)):
                raise ValidationError(
                    _("Tax names must be unique!")
                    + "\n" + "\n".join(_(
                        "- %(name)s in %(company)s",
                        name=duplicate.name,
                        company=duplicate.company_id.name,
                    ) for duplicate in duplicates)
                )

    @api.constrains('tax_group_id')
    def validate_tax_group_id(self):
        for record in self:
            if record.tax_group_id.country_id and record.tax_group_id.country_id != record.country_id:
                raise ValidationError(_("The tax group must have the same country_id as the tax using it."))

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
        if isinstance(value, bool):
            tax_value = 'tax_included' if value else 'tax_excluded'
            return [
                '|', ('price_include_override', operator, tax_value),
                    '&', ('price_include_override', '=', False),
                         ('company_price_include', operator, tax_value),
            ]
        raise NotImplementedError()

    def _hook_compute_is_used(self, tax_to_compute):
        '''
            Override to compute the ids of taxes used in other modules. It takes
            as parameter a set of tax ids. It should return a set containing the
            ids of the taxes from that input set that are used in transactions.
        '''
        return set()

    def _compute_is_used(self):
        used_taxes = set()

        # Fetch for taxes used in account moves
        self.env['account.move.line'].flush_model(['tax_ids'])
        self.env.cr.execute("""
            SELECT id
            FROM account_tax
            WHERE EXISTS(
                SELECT 1
                FROM account_move_line_account_tax_rel AS line
                WHERE account_tax_id IN %s
                AND account_tax.id = line.account_tax_id
            )
        """, [tuple(self.ids)])
        used_taxes.update([tax[0] for tax in self.env.cr.fetchall()])
        taxes_to_compute = set(self.ids) - used_taxes

        # Fetch for taxes used in reconciliation
        if taxes_to_compute:
            self.env['account.reconcile.model.line'].flush_model(['tax_ids'])
            self.env.cr.execute("""
                SELECT id
                FROM account_tax
                WHERE EXISTS(
                    SELECT 1
                    FROM account_reconcile_model_line_account_tax_rel AS reco
                    WHERE account_tax_id IN %s
                    AND account_tax.id = reco.account_tax_id
                )
            """, [tuple(taxes_to_compute)])
            used_taxes.update([tax[0] for tax in self.env.cr.fetchall()])
            taxes_to_compute -= used_taxes

        # Fetch for tax used in other modules
        if taxes_to_compute:
            used_taxes.update(self._hook_compute_is_used(taxes_to_compute))

        for tax in self:
            tax.is_used = tax.id in used_taxes

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

        old_line_values_dict = ast.literal_eval(old_values_str)
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
    def _search_display_name(self, operator, value):
        if operator in ("ilike", "like"):
            value = AccountTax._parse_name_search(value)
        return super()._search_display_name(operator, value)

    def _search_name(self, operator, value):
        if operator not in ("ilike", "like") or not isinstance(value, str):
            return [('name', operator, value)]
        return [('name', operator, AccountTax._parse_name_search(value))]

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
                vals['name'] = _("%s (Copy)", tax.name)
        return vals_list

    @api.depends('type_tax_use', 'tax_scope')
    @api.depends_context('append_type_to_tax_name')
    def _compute_display_name(self):
        type_tax_use = dict(self._fields['type_tax_use']._description_selection(self.env))
        for record in self:
            if name := record.name:
                if self._context.get('append_type_to_tax_name'):
                    name += ' (%s)' % type_tax_use.get(record.type_tax_use)
                if len(self.env.companies) > 1 and self.env.context.get('params', {}).get('model') == 'product.template':
                    name += ' (%s)' % record.company_id.display_name
                if record.country_id != record.company_id._accessible_branches()[:1].account_fiscal_country_id:
                    name += ' (%s)' % record.country_code
            record.display_name = name

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

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        Note: In javascript, this method takes an additional parameter being the results of the
        '_eval_taxes_computation_prepare_product_default_values' method because this method is not callable in javascript but must
        be passed to the client instead.

        :param default_product_values:  The default product values generated by '_eval_taxes_computation_prepare_product_default_values'.
        :param product:                 An optional product.product record.
        :return:                        The values representing the product.
        """
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

        :param product: An optional product.product record.
        :return:        The values representing the product.
        """
        product_fields = self._eval_taxes_computation_prepare_product_fields()
        default_product_values = self._eval_taxes_computation_prepare_product_default_values(product_fields)
        return self._eval_taxes_computation_prepare_product_values(
            default_product_values=default_product_values,
            product=product,
        )

    def _batch_for_taxes_computation(self, special_mode=False):
        """ Group the current taxes all together like price-included percent taxes or division taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param special_mode: The special mode of the taxes computation: False, 'total_excluded' or 'total_included'.
        :return: A dictionary containing:
            * batch_per_tax: A mapping of each tax to its batch.
            * group_per_tax: A mapping of each tax retrieved from a group of taxes.
            * sorted_taxes: A recordset of all taxes in the order on which they need to be evaluated.
                            Note that we consider the sequence of the parent for group of taxes.
                            Eg. considering letters as taxes and alphabetic order as sequence :
                            [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]
        """
        def sort_key(tax):
            return tax.sequence, tax.id

        results = {
            'batch_per_tax': {},
            'group_per_tax': {},
            'sorted_taxes': self.env['account.tax'],
        }

        # Flatten the taxes.
        for tax in self.sorted(key=sort_key):
            if tax.amount_type == 'group':
                children = tax.children_tax_ids.sorted(key=sort_key)
                results['sorted_taxes'] |= children
                for child in children:
                    results['group_per_tax'][child.id] = tax
            else:
                results['sorted_taxes'] |= tax

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
                if not tax.include_base_amount:
                    for other_tax in get_tax_after():
                        if other_tax.price_include:
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
                for other_tax in get_tax_after():
                    if not other_tax.price_include or tax.include_base_amount:
                        add_extra_base(other_tax, 1)

        elif not tax.price_include:

            # Case of a tax affecting the base of the subsequent ones, no price included taxes.
            if special_mode in (False, 'total_excluded'):
                if tax.include_base_amount:
                    for other_tax in get_tax_after():
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
            return evaluation_context['quantity'] * self.amount

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
        special_mode=False,
    ):
        """ Compute the tax/base amounts for the current taxes.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param price_unit:          The price unit of the line.
        :param quantity:            The quantity of the line.
        :param precision_rounding:  The rounding precision for the 'round_per_line' method.
        :param rounding_method:     'round_per_line' or 'round_globally'.
        :param product:             The product of the line.
        :param special_mode:        Indicate a special mode for the taxes computation.
                            * total_excluded: The initial base of computation excludes all price-included taxes.
                            Suppose a tax of 21% price included. Giving 100 with special_mode = 'total_excluded'
                            will give you the same as 121 without any special_mode.
                            * total_included: The initial base of computation is the total with taxes.
                            Suppose a tax of 21% price excluded. Giving 121 with special_mode = 'total_included'
                            will give you the same as 100 without any special_mode.
                            Note: You can only expect accurate symmetrical taxes computation with not rounded price_unit
                            as input and 'round_globally' computation. Otherwise, it's not guaranteed.
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
            if special_mode == 'total_included':
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

        # Flatten the taxes and order them.
        batching_results = self._batch_for_taxes_computation(special_mode=special_mode)
        sorted_taxes = batching_results['sorted_taxes']
        taxes_data = {}
        for tax in sorted_taxes:
            taxes_data[tax.id] = prepare_tax_extra_data(
                tax,
                group=batching_results['group_per_tax'].get(tax.id),
                batch=batching_results['batch_per_tax'][tax.id],
            )

        raw_base = quantity * price_unit
        if rounding_method == 'round_per_line':
            raw_base = float_round(raw_base, precision_rounding=precision_rounding)

        evaluation_context = {
            'product': sorted_taxes._eval_taxes_computation_turn_to_product_values(product=product),
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
        for tax in reversed(sorted_taxes):
            if 'tax_amount' not in taxes_data[tax.id]:
                continue

            total_tax_amount = sum(taxes_data[other_tax.id]['tax_amount'] for other_tax in taxes_data[tax.id]['batch'])
            base = raw_base + taxes_data[tax.id]['extra_base_for_base']
            if taxes_data[tax.id]['price_include'] and special_mode in (False, 'total_included'):
                base -= total_tax_amount
            taxes_data[tax.id]['base'] = base

        taxes_data_list = [tax_data for tax_data in taxes_data.values() if 'tax_amount' in tax_data]

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
                    'group': batching_results['group_per_tax'].get(tax_data['tax'].id) or self.env['account.tax'],
                    'batch': batching_results['batch_per_tax'][tax_data['tax'].id],
                    'tax_amount': tax_data['tax_amount'],
                    'base_amount': tax_data['base'],
                }
                for tax_data in taxes_data_list
            ],
            'tax_data_index': {
                tax_data['tax'].id: index
                for index, tax_data in enumerate(taxes_data_list)
            },
        }

    # -------------------------------------------------------------------------
    # MAPPING PRICE_UNIT
    # -------------------------------------------------------------------------

    @api.model
    def _adapt_price_unit_to_another_taxes(self, price_unit, product, original_taxes, new_taxes):
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
        )
        price_unit = taxes_computation['total_excluded']

        # Find the new price unit after applying the price included taxes.
        taxes_computation = new_taxes._get_tax_details(
            price_unit,
            1.0,
            rounding_method='round_globally',
            product=product,
            special_mode='total_excluded',
        )
        delta = sum(x['tax_amount'] for x in taxes_computation['taxes_data'] if x['tax'].price_include)
        return price_unit + delta

    # -------------------------------------------------------------------------
    # END HELPERS IN BOTH PYTHON/JAVASCRIPT (account_tax.js)
    # -------------------------------------------------------------------------

    @api.model
    def _apply_taxes_computation_split_repartition_lines(
        self,
        taxes_data,
        currency,
        is_refund=False,
        include_caba_tags=False,
        rounding_method='round_per_line',
    ):
        if is_refund:
            repartition_lines_field = 'refund_repartition_line_ids'
        else:
            repartition_lines_field = 'invoice_repartition_line_ids'

        tax_rep_values_list = []
        for tax_data in taxes_data:
            tax = tax_data['tax']

            # Split naively by repartition line.
            rep_lines = tax[repartition_lines_field].filtered(lambda x: x.repartition_type == 'tax')
            repartition_line_amounts = [tax_data['tax_amount'] * line.factor for line in rep_lines]
            if rounding_method == 'round_per_line':
                repartition_line_amounts = [currency.round(x) for x in repartition_line_amounts]
            total_repartition_line_amount = sum(repartition_line_amounts)

            # Fix the rounding error caused by rounding.
            total_factor = sum(rep_lines.mapped('factor'))
            total_tax_amount = tax_data['tax_amount'] * total_factor
            if rounding_method == 'round_per_line':
                total_tax_amount = currency.round(total_tax_amount)
            total_error = total_tax_amount - total_repartition_line_amount
            error_sign = -1 if total_error < 0.0 else 1
            total_error *= error_sign
            for index, _amount in enumerate(repartition_line_amounts):
                if not total_error:
                    break

                # Don't allocate more than one currency unit.
                # The error is smoothly dispatched on repartition lines.
                # If you have 5 repartition lines and 0.03 to dispatch, three of them will take 0.01 instead of
                # only one getting 0.03.
                error = min(total_error, currency.rounding)
                total_error -= error
                repartition_line_amounts[index] += error_sign * error

            for rep_line, line_amount in zip(rep_lines, repartition_line_amounts):

                # Tags.
                if not include_caba_tags and tax.tax_exigibility == 'on_payment':
                    rep_line_tags = self.env['account.account.tag']
                else:
                    rep_line_tags = rep_line.tag_ids

                tax_rep_values_list.append({
                    **tax_data,
                    'tax_amount': line_amount,
                    'tax_repartition_line': rep_line,
                    'tags': tax_data['tags'] | rep_line_tags,
                })
        return tax_rep_values_list

    def flatten_taxes_hierarchy(self):
        # Flattens the taxes contained in this recordset, returning all the
        # children at the bottom of the hierarchy, in a recordset, ordered by sequence.
        #   Eg. considering letters as taxes and alphabetic order as sequence :
        #   [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]
        # If create_map is True, an additional value is returned, a dictionary
        # mapping each child tax to its parent group
        all_taxes = self.env['account.tax']
        for tax in self.sorted(key=lambda r: r.sequence):
            if tax.amount_type == 'group':
                all_taxes += tax.children_tax_ids.flatten_taxes_hierarchy()
            else:
                all_taxes += tax
        return all_taxes

    def get_tax_tags(self, is_refund, repartition_type):
        document_type = 'refund' if is_refund else 'invoice'
        return self.repartition_line_ids\
            .filtered(lambda x: x.repartition_type == repartition_type and x.document_type == document_type)\
            .mapped('tag_ids')

    @api.model
    def _prepare_base_line_tax_details(
        self,
        base_line,
        company,
        rounding_method=None,
        include_caba_tags=False,
    ):
        # Prepare computation of python taxes (see the 'account_tax_python' module).
        price_unit = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        quantity = base_line['quantity']
        product = base_line['product']

        # Prepare the tax computation.
        taxes = base_line['taxes']._origin
        is_refund = base_line['is_refund']
        if rounding_method is None:
            rounding_method = company.tax_calculation_rounding_method
        currency = base_line['currency'] or company.currency_id
        if (force_price_include := base_line['extra_context'].get('force_price_include')) is not None:
            special_mode = 'total_included' if force_price_include else 'total_excluded'
        elif not base_line['handle_price_include']:
            special_mode = 'total_excluded'
        else:
            special_mode = False

        taxes_computation = taxes._get_tax_details(
            price_unit,
            quantity,
            precision_rounding=currency.rounding,
            rounding_method=rounding_method,
            product=product,
            special_mode=special_mode,
        )
        taxes_data = taxes_computation['taxes_data']

        # Tags on the base line.
        if is_refund:
            repartition_lines_field = 'refund_repartition_line_ids'
        else:
            repartition_lines_field = 'invoice_repartition_line_ids'
        base_tags = self.env['account.account.tag']
        for tax_data in taxes_data:
            tax = tax_data['tax']
            if include_caba_tags or tax.tax_exigibility != 'on_payment':
                base_tags |= tax[repartition_lines_field].filtered(lambda x: x.repartition_type == 'base').tag_ids
        if product:
            base_tags |= product.sudo().account_tag_ids

        # Compute subsequent taxes/tags & 'display_base' for the tax totals.
        subsequent_taxes = self.env['account.tax']
        subsequent_tags = self.env['account.account.tag']
        for tax_data in reversed(taxes_computation['taxes_data']):
            tax = tax_data['tax']
            batch = tax_data['batch']
            batch_taxes_data = [
                taxes_computation['taxes_data'][batch_tax_data_index]
                for batch_tax in batch
                if (batch_tax_data_index := taxes_computation['tax_data_index'].get(batch_tax.id)) is not None
            ]

            # Fill 'taxes' / 'tags'.
            if 'taxes' not in tax_data:
                for batch_tax_data in batch_taxes_data:
                    batch_tax_data['taxes'] = subsequent_taxes if tax.include_base_amount else self.env['account.tax']
                    batch_tax_data['tags'] = subsequent_tags if tax.include_base_amount else self.env['account.account.tag']
            subsequent_taxes |= batch
            if include_caba_tags or tax.tax_exigibility == 'on_invoice':
                subsequent_tags |= tax[repartition_lines_field].filtered(lambda x: x.repartition_type == 'base').tag_ids

            # Compute 'display_base'.
            total_batch_amount = sum(batch_tax_data['tax_amount'] for batch_tax_data in batch_taxes_data)
            if tax.amount_type == 'division' and tax.price_include:
                tax_data['display_base'] = tax_data['base_amount'] + total_batch_amount
            else:
                tax_data['display_base'] = tax_data['base_amount']

        # Repartition lines.
        taxes_data = taxes._apply_taxes_computation_split_repartition_lines(
            taxes_data,
            currency,
            is_refund=is_refund,
            include_caba_tags=include_caba_tags,
            rounding_method=rounding_method,
        )

        # Apply the rate.
        for tax_data in taxes_data:
            rate = base_line.get('rate') or 1.0
            tax_data['display_base_amount_currency'] = tax_data['display_base']
            tax_data['display_base_amount'] = tax_data['display_base_amount_currency'] / rate if rate else 0.0
            tax_data['base_amount_currency'] = tax_data['base_amount']
            tax_data['base_amount'] = tax_data['base_amount_currency'] / rate if rate else 0.0
            tax_data['tax_amount_currency'] = tax_data['tax_amount']
            tax_data['tax_amount'] = tax_data['tax_amount_currency'] / rate if rate else 0.0
            if rounding_method == 'round_per_line':
                tax_data['display_base_amount_currency'] = currency.round(tax_data['display_base_amount_currency'])
                tax_data['display_base_amount'] = company.currency_id.round(tax_data['display_base_amount'])
                tax_data['base_amount_currency'] = currency.round(tax_data['base_amount_currency'])
                tax_data['base_amount'] = company.currency_id.round(tax_data['base_amount'])
                tax_data['tax_amount_currency'] = currency.round(tax_data['tax_amount_currency'])
                tax_data['tax_amount'] = company.currency_id.round(tax_data['tax_amount'])

        return {
            'base_tags': base_tags,
            'total_excluded': taxes_computation['total_excluded'],
            'total_included': taxes_computation['total_included'],
            'taxes_data': taxes_data,
        }

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True, include_caba_tags=False, rounding_method=None):
        """Compute all information required to apply taxes (in self + their children in case of a tax group).
        We consider the sequence of the parent for group of taxes.
            Eg. considering letters as taxes and alphabetic order as sequence :
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
        :return: {
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
        } """
        if not self:
            company = self.env.company
        else:
            company = self[0].company_id._accessible_branches()[:1] or self[0].company_id

        # Compute tax details for a single line.
        currency = currency or company.currency_id
        base_line = self._convert_to_tax_base_line_dict(
            None,
            partner=partner,
            currency=currency,
            product=product,
            taxes=self,
            price_unit=price_unit,
            quantity=quantity,
            is_refund=is_refund,
            handle_price_include=handle_price_include,
            extra_context={'force_price_include': self._context.get('force_price_include')},
        )
        results = self._prepare_base_line_tax_details(
            base_line,
            company,
            rounding_method=rounding_method,
            include_caba_tags=include_caba_tags,
        )
        taxes_data = results['taxes_data']
        base_tags = results['base_tags']
        total_excluded = results['total_excluded']
        total_included = results['total_included']

        total_void = total_excluded + sum(
            tax_data['tax_amount_currency']
            for tax_data in taxes_data
            if not tax_data['tax_repartition_line'].account_id
        )

        # Convert to the 'old' compute_all api.
        taxes = []
        for tax_data in taxes_data:
            tax = tax_data['tax']
            rep_line = tax_data['tax_repartition_line']
            taxes.append({
                'id': tax.id,
                'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
                'amount': tax_data['tax_amount_currency'],
                'base': tax_data['base_amount_currency'],
                'sequence': tax.sequence,
                'account_id': rep_line._get_aml_target_tax_account(force_caba_exigibility=include_caba_tags).id,
                'analytic': tax.analytic,
                'use_in_tax_closing': rep_line.use_in_tax_closing,
                'price_include': tax_data['tax'].price_include,
                'tax_exigibility': tax.tax_exigibility,
                'tax_repartition_line_id': rep_line.id,
                'group': tax_data['group'],
                'tag_ids': tax_data['tags'].ids,
                'tax_ids': tax_data['taxes'].ids,
            })

        if self._context.get('round_base', True):
            total_excluded = currency.round(total_excluded)
            total_included = currency.round(total_included)

        return {
            'base_tags': base_tags.ids,
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
            company = company.parent_id
        return taxes

    @api.model
    def _convert_to_tax_base_line_dict(
            self, base_line,
            partner=None, currency=None, product=None, taxes=None, price_unit=None, quantity=None,
            discount=None, account=None, analytic_distribution=None, price_subtotal=None,
            is_refund=False, rate=None,
            handle_price_include=True,
            extra_context=None,
    ):
        if product and product._name == 'product.template':
            product = product.product_variant_id
        return {
            'record': base_line,
            'partner': partner or self.env['res.partner'],
            'currency': currency or self.env['res.currency'],
            'product': product or self.env['product.product'],
            'taxes': taxes or self.env['account.tax'],
            'price_unit': price_unit or 0.0,
            'quantity': quantity or 0.0,
            'discount': discount or 0.0,
            'account': account or self.env['account.account'],
            'analytic_distribution': analytic_distribution,
            'price_subtotal': price_subtotal or 0.0,
            'is_refund': is_refund,
            'rate': rate or 1.0,
            'handle_price_include': handle_price_include,
            'extra_context': extra_context or {},
        }

    @api.model
    def _convert_to_tax_line_dict(
            self, tax_line,
            partner=None, currency=None, taxes=None, tax_tags=None, tax_repartition_line=None,
            group_tax=None, account=None, analytic_distribution=None, tax_amount_currency=None, tax_amount=None,
    ):
        return {
            'record': tax_line,
            'partner': partner or self.env['res.partner'],
            'currency': currency or self.env['res.currency'],
            'taxes': taxes or self.env['account.tax'],
            'tax_tags': tax_tags or self.env['account.account.tag'],
            'tax_repartition_line': tax_repartition_line or self.env['account.tax.repartition.line'],
            'group_tax': group_tax or self.env['account.tax'],
            'account': account or self.env['account.account'],
            'analytic_distribution': analytic_distribution,
            'tax_amount_currency': tax_amount_currency or 0.0,
            'tax_amount': tax_amount or 0.0,
        }

    @api.model
    def _get_generation_dict_from_base_line(self, line_vals, tax_vals, force_caba_exigibility=False):
        """ Take a tax results returned by the taxes computation method and return a dictionary representing the way
        the tax amounts will be grouped together. To do so, the dictionary will be converted into a string key.
        Then, the existing tax lines sharing the same key will be updated and the missing ones will be created.

        :param line_vals:   A python dict returned by '_convert_to_tax_base_line_dict'.
        :param tax_vals:    A python dict returned by 'compute_all' under the 'taxes' key.
        :return:            A python dict.
        """
        tax_repartition_line = tax_vals['tax_repartition_line']
        tax = tax_repartition_line.tax_id
        tax_account = tax_repartition_line._get_aml_target_tax_account(force_caba_exigibility=force_caba_exigibility) or line_vals['account']
        return {
            'account_id': tax_account.id,
            'currency_id': line_vals['currency'].id,
            'partner_id': line_vals['partner'].id,
            'tax_repartition_line_id': tax_repartition_line.id,
            'tax_ids': [Command.set(tax_vals['taxes'].ids)],
            'tax_tag_ids': [Command.set(tax_vals['tags'].ids)],
            'tax_id': tax_vals['group'].id if tax_vals.get('group') else tax.id,
            'analytic_distribution': line_vals['analytic_distribution'] if tax.analytic else {},
        }

    @api.model
    def _get_generation_dict_from_tax_line(self, line_vals):
        """ Turn the values corresponding to a tax line and convert it into a dictionary. The dictionary will be
        converted into a string key. This allows updating the existing tax lines instead of creating new ones
        everytime.

        :param line_vals:   A python dict returned by '_convert_to_tax_line_dict'.
        :return:            A python dict representing the grouping key used to update an existing tax line.
        """
        tax = line_vals['tax_repartition_line'].tax_id
        return {
            'account_id': line_vals['account'].id,
            'currency_id': line_vals['currency'].id,
            'partner_id': line_vals['partner'].id,
            'tax_repartition_line_id': line_vals['tax_repartition_line'].id,
            'tax_ids': [Command.set(line_vals['taxes'].ids)],
            'tax_tag_ids': [Command.set(line_vals['tax_tags'].ids)],
            'tax_id': (line_vals['group_tax'] or tax).id,
            'analytic_distribution': line_vals['analytic_distribution'] if tax.analytic else {},
        }

    @api.model
    def _aggregate_taxes(self, to_process, company, filter_tax_values_to_apply=None, grouping_key_generator=None, distribute_total_on_line=True):

        def default_grouping_key_generator(base_line, tax_values):
            return {'tax': tax_values['tax_repartition_line'].tax_id}

        def accounting_grouping_key_generator(base_line, tax_values):
            return self._get_generation_dict_from_base_line(base_line, tax_values)

        results = {
            'base_amount_currency': 0.0,
            'base_amount': 0.0,
            'display_base_amount_currency': 0.0,
            'display_base_amount': 0.0,
            'tax_amount_currency': defaultdict(lambda: 0.0),
            'tax_amount': defaultdict(lambda: 0.0),
            'tax_details': defaultdict(lambda: {
                'base_amount_currency': 0.0,
                'base_amount': 0.0,
                'display_base_amount_currency': 0.0,
                'display_base_amount': 0.0,
                'tax_amount_currency': defaultdict(lambda: 0.0),
                'tax_amount': defaultdict(lambda: 0.0),
                'group_tax_details': [],
                'records': set(),
            }),
            'tax_details_per_record': defaultdict(lambda: {
                'base_amount_currency': 0.0,
                'base_amount': 0.0,
                'display_base_amount_currency': 0.0,
                'display_base_amount': 0.0,
                'tax_amount_currency': defaultdict(lambda: 0.0),
                'tax_amount': defaultdict(lambda: 0.0),
                'tax_details': defaultdict(lambda: {
                    'base_amount_currency': 0.0,
                    'base_amount': 0.0,
                    'display_base_amount_currency': 0.0,
                    'display_base_amount': 0.0,
                    'tax_amount_currency': defaultdict(lambda: 0.0),
                    'tax_amount': defaultdict(lambda: 0.0),
                    'group_tax_details': [],
                    'records': set(),
                }),
            }),
        }

        if not grouping_key_generator:
            grouping_key_generator = default_grouping_key_generator

        comp_currency = company.currency_id
        round_tax = company.tax_calculation_rounding_method != 'round_globally'
        if company.tax_calculation_rounding_method == 'round_globally' and distribute_total_on_line:
            # Aggregate all amounts according the tax lines grouping key.
            amount_per_tax_repartition_line_id = defaultdict(lambda: {
                'tax_amount': 0.0,
                'tax_amount_currency': 0.0,
                'taxes_data': [],
            })
            for base_line, tax_details_results in to_process:
                currency = base_line['currency'] or comp_currency
                for tax_data in tax_details_results['taxes_data']:
                    grouping_key = frozendict(self._get_generation_dict_from_base_line(base_line, tax_data))
                    total_amounts = amount_per_tax_repartition_line_id[grouping_key]
                    total_amounts['tax_amount_currency'] += tax_data['tax_amount_currency']
                    total_amounts['tax_amount'] += tax_data['tax_amount']
                    total_amounts['taxes_data'].append(tax_data)
            # Round them like what the creation of tax lines would do.
            for key, values in amount_per_tax_repartition_line_id.items():
                currency = self.env['res.currency'].browse(key['currency_id']) or comp_currency
                values['tax_amount_rounded'] = comp_currency.round(values['tax_amount'])
                values['tax_amount_currency_rounded'] = currency.round(values['tax_amount_currency'])
            # Dispatch the amount accross the tax values.
            for key, values in amount_per_tax_repartition_line_id.items():
                foreign_currency = self.env['res.currency'].browse(key['currency_id']) or comp_currency
                for currency, amount_field in ((comp_currency, 'tax_amount'), (foreign_currency, 'tax_amount_currency')):
                    raw_value = values[amount_field]
                    rounded_value = values[f'{amount_field}_rounded']
                    diff = rounded_value - raw_value
                    abs_diff = abs(diff)
                    diff_sign = -1 if diff < 0 else 1
                    taxes_data = values['taxes_data']
                    nb_error = math.ceil(abs_diff / currency.rounding)
                    nb_cents_per_tax_values = math.floor(nb_error / len(taxes_data))
                    nb_extra_cent = nb_error % len(taxes_data)
                    for tax_data in taxes_data:
                        if not abs_diff:
                            break
                        nb_amount_curr_cent = nb_cents_per_tax_values
                        if nb_extra_cent:
                            nb_amount_curr_cent += 1
                            nb_extra_cent -= 1
                        # We can have more than one cent to distribute on a single tax_values.
                        abs_delta_to_add = min(abs_diff, currency.rounding * nb_amount_curr_cent)
                        tax_data[amount_field] += diff_sign * abs_delta_to_add
                        abs_diff -= abs_delta_to_add

        for base_line, tax_details_results in to_process:
            record = base_line['record']
            currency = base_line['currency'] or comp_currency

            record_results = results['tax_details_per_record'][record]

            base_added = False
            base_grouping_key_added = set()
            for tax_data in tax_details_results['taxes_data']:
                if filter_tax_values_to_apply and not filter_tax_values_to_apply(base_line, tax_data):
                    continue

                grouping_key = frozendict(grouping_key_generator(base_line, tax_data))
                accounting_grouping_key = frozendict(accounting_grouping_key_generator(base_line, tax_data))
                base_amount_currency = tax_data['base_amount_currency']
                base_amount = tax_data['base_amount']
                display_base_amount_currency = tax_data['display_base_amount_currency']
                display_base_amount = tax_data['display_base_amount']

                if round_tax:
                    tax_data['base_amount_currency'] = currency.round(tax_data['base_amount_currency'])
                    tax_data['base_amount'] = comp_currency.round(tax_data['base_amount'])
                    tax_data['display_base_amount_currency'] = currency.round(tax_data['display_base_amount_currency'])
                    tax_data['display_base_amount'] = comp_currency.round(tax_data['display_base_amount'])

                # 'global' base.
                if not base_added:
                    base_added = True
                    for sub_results in (results, record_results):
                        sub_results['base_amount_currency'] += base_amount_currency
                        sub_results['base_amount'] += base_amount
                        sub_results['display_base_amount_currency'] += display_base_amount_currency
                        sub_results['display_base_amount'] += display_base_amount
                        sub_results['currency'] = currency

                # 'local' base.
                global_local_results = results['tax_details'][grouping_key]
                record_local_results = record_results['tax_details'][grouping_key]
                if grouping_key not in base_grouping_key_added:
                    base_grouping_key_added.add(grouping_key)
                    for sub_results in (global_local_results, record_local_results):
                        sub_results.update(grouping_key)
                        sub_results['base_amount_currency'] += base_amount_currency
                        sub_results['base_amount'] += base_amount
                        sub_results['display_base_amount_currency'] += display_base_amount_currency
                        sub_results['display_base_amount'] += display_base_amount
                        sub_results['currency'] = currency
                        sub_results['records'].add(record)
                        sub_results['group_tax_details'].append(tax_data)

                # 'global'/'local' tax amount.
                for sub_results in (results, record_results, global_local_results, record_local_results):
                    sub_results['tax_amount_currency'][accounting_grouping_key] += tax_data['tax_amount_currency']
                    sub_results['tax_amount'][accounting_grouping_key] += tax_data['tax_amount']
                    sub_results['currency'] = currency

            # Rounding of tax amounts for the line.
            for sub_results in [record_results] + list(record_results['tax_details'].values()):
                for currency, key in ((sub_results.get('currency'), 'tax_amount_currency'), (comp_currency, 'tax_amount')):
                    if currency and round_tax:
                        for grouping_key, amount in sub_results[key].items():
                            sub_results[key][grouping_key] = currency.round(amount)

            for sub_results in [record_results] + list(record_results['tax_details'].values()):
                for key in ('tax_amount_currency', 'tax_amount'):
                    sub_results[key] = sum(sub_results[key].values())

        # Rounding of tax amounts.
        for sub_results in [results] + list(results['tax_details'].values()):
            for currency, key in ((sub_results.get('currency'), 'tax_amount_currency'), (comp_currency, 'tax_amount')):
                if currency and round_tax:
                    for grouping_key, amount in sub_results[key].items():
                        sub_results[key][grouping_key] = currency.round(amount)

        for sub_results in [results] + list(results['tax_details'].values()):
            for key in ('tax_amount_currency', 'tax_amount'):
                sub_results[key] = sum(sub_results[key].values())

        return results

    @api.model
    def _compute_taxes(self, base_lines, company, tax_lines=None, include_caba_tags=False):
        """ Generic method to compute the taxes for different business models.

        :param base_lines: A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param company: The company to consider.
        :param tax_lines: A list of python dictionaries created using the '_convert_to_tax_line_dict' method.
        :param include_caba_tags: Manage tags for taxes being exigible on_payment.
        :return: A python dictionary containing:

            The complete diff on tax lines if 'tax_lines' is passed as parameter:
            * tax_lines_to_add:     To create new tax lines.
            * tax_lines_to_delete:  To track the tax lines that are no longer used.
            * tax_lines_to_update:  The values to update the existing tax lines.

            * base_lines_to_update: The values to update the existing base lines:
                * tax_tag_ids:          The tags related to taxes.
                * price_subtotal:       The amount without tax.
                * price_total:          The amount with taxes.

            * totals:               A mapping for each involved currency to:
                * amount_untaxed:       The base amount without tax.
                * amount_tax:           The total tax amount.
        """
        res = {
            'tax_lines_to_add': [],
            'tax_lines_to_delete': [],
            'tax_lines_to_update': [],
            'base_lines_to_update': [],
            'totals': defaultdict(lambda: {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
            }),
        }

        # =========================================================================================
        # BASE LINES
        # For each base line, populate 'base_lines_to_update'.
        # Compute 'tax_base_amount'/'tax_amount' for each pair <base line, tax repartition line>
        # using the grouping key generated by the '_get_generation_dict_from_base_line' method.
        # =========================================================================================

        # Prepare the tax details for each line.
        to_process = []
        for base_line in base_lines:
            tax_details_results = self._prepare_base_line_tax_details(
                base_line,
                company,
                include_caba_tags=include_caba_tags,
            )
            to_process.append((base_line, tax_details_results))

        # Fill 'base_lines_to_update' and 'totals'.
        for base_line, tax_details_results in to_process:
            res['base_lines_to_update'].append((base_line, {
                'tax_tag_ids': [Command.set(tax_details_results['base_tags'].ids)],
                'price_subtotal': tax_details_results['total_excluded'],
                'price_total': tax_details_results['total_included'],
            }))

            currency = base_line['currency'] or company.currency_id
            res['totals'][currency]['amount_untaxed'] += tax_details_results['total_excluded']

        # =========================================================================================
        # TAX LINES
        # Map each existing tax lines using the grouping key generated by the
        # '_get_generation_dict_from_tax_line' method.
        # Since everything is indexed using the grouping key, we are now able to decide if
        # (1) we can reuse an existing tax line and update its amounts
        # (2) some tax lines are no longer used and can be dropped
        # (3) we need to create new tax lines
        # =========================================================================================

        # Track the existing tax lines using the grouping key.
        existing_tax_line_map = {}
        for line_vals in tax_lines or []:
            grouping_key = frozendict(self._get_generation_dict_from_tax_line(line_vals))

            # After a modification (e.g. changing the analytic account of the tax line), if two tax lines are sharing
            # the same key, keep only one.
            if grouping_key in existing_tax_line_map:
                res['tax_lines_to_delete'].append(line_vals)
            else:
                existing_tax_line_map[grouping_key] = line_vals

        def grouping_key_generator(base_line, tax_data):
            return self._get_generation_dict_from_base_line(base_line, tax_data, force_caba_exigibility=include_caba_tags)

        # Update/create the tax lines.
        global_tax_details = self._aggregate_taxes(to_process, company, grouping_key_generator=grouping_key_generator)

        for grouping_key, tax_data in global_tax_details['tax_details'].items():
            if tax_data['currency_id']:
                currency = self.env['res.currency'].browse(tax_data['currency_id'])
                tax_amount = currency.round(tax_data['tax_amount_currency'])
                res['totals'][currency]['amount_tax'] += tax_amount

            if grouping_key in existing_tax_line_map:
                # Update an existing tax line.
                line_vals = existing_tax_line_map.pop(grouping_key)
                res['tax_lines_to_update'].append((line_vals, tax_data))
            else:
                # Create a new tax line.
                res['tax_lines_to_add'].append(tax_data)

        for line_vals in existing_tax_line_map.values():
            res['tax_lines_to_delete'].append(line_vals)

        return res

    @api.model
    def _prepare_tax_totals(self, base_lines, currency, company, tax_lines=None):
        """ Compute the tax totals details for the business documents.
        :param base_lines:                      A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param currency:                        The currency set on the business document.
        :param company:                         The company to consider.
        :param tax_lines:                       Optional list of python dictionaries created using the '_convert_to_tax_line_dict'
                                                method. If specified, the taxes will be recomputed using them instead of
                                                recomputing the taxes on the provided base lines.
        :return: A dictionary in the following form:
            {
                'amount_total':                 The total amount to be displayed on the document, including every total
                                                types.
                'amount_untaxed':               The untaxed amount to be displayed on the document.
                'formatted_amount_total':       Same as amount_total, but as a string formatted accordingly with
                                                partner's locale.
                'formatted_amount_untaxed':     Same as amount_untaxed, but as a string formatted accordingly with
                                                partner's locale.
                'groups_by_subtotals':          A dictionary formed liked {'subtotal': groups_data}
                                                Where total_type is a subtotal name defined on a tax group, or the
                                                default one: 'Untaxed Amount'.
                                                And groups_data is a list of dict in the following form:
                    {
                        'tax_group_name':                           The name of the tax groups this total is made for.
                        'tax_group_amount':                         The total tax amount in this tax group.
                        'tax_group_base_amount':                    The base amount for this tax group.
                        'formatted_tax_group_amount':               Same as tax_group_amount, but as a string formatted accordingly
                                                                    with partner's locale.
                        'formatted_tax_group_base_amount':          Same as tax_group_base_amount, but as a string formatted
                                                                    accordingly with partner's locale.
                        'tax_group_id':                             The id of the tax group corresponding to this dict.
                        'tax_group_base_amount_company_currency':   OPTIONAL: the base amount of the tax group expressed in
                                                                    the company currency when the parameter
                                                                    is_company_currency_requested is True
                        'tax_group_amount_company_currency':        OPTIONAL: the tax amount of the tax group expressed in
                                                                    the company currency when the parameter
                                                                    is_company_currency_requested is True
                    }
                'subtotals':                    A list of dictionaries in the following form, one for each subtotal in
                                                'groups_by_subtotals' keys.
                    {
                        'name':                             The name of the subtotal
                        'amount':                           The total amount for this subtotal, summing all the tax groups
                                                            belonging to preceding subtotals and the base amount
                        'formatted_amount':                 Same as amount, but as a string formatted accordingly with
                                                            partner's locale.
                        'amount_company_currency':          OPTIONAL: The total amount in company currency when the
                                                            parameter is_company_currency_requested is True
                    }
                'subtotals_order':              A list of keys of `groups_by_subtotals` defining the order in which it needs
                                                to be displayed
            }
        """
        comp_curr = company.currency_id

        # ==== Compute the taxes ====

        # Round according the tax lines.
        target_tax_details_by_tax = defaultdict(lambda: [0.0, 0.0])
        for tax_line in tax_lines or []:
            tax_id = tax_line['tax_repartition_line'].tax_id.id
            target_tax_details_by_tax[tax_id][0] += tax_line['tax_amount']
            target_tax_details_by_tax[tax_id][1] += tax_line['tax_amount_currency']

        # Prepare the tax details for each line.
        tax_details_by_tax = defaultdict(list)
        to_process = []
        for base_line in base_lines:
            tax_details_results = self._prepare_base_line_tax_details(base_line, company)
            to_process.append((base_line, tax_details_results))

            # Add 'display_base'.
            for tax_data in tax_details_results['taxes_data']:
                tax = tax_data['tax']
                tax_details_by_tax[tax.id].append(tax_data)
                if tax.id in target_tax_details_by_tax:
                    target_tax_details_by_tax[tax.id][0] -= tax_data['tax_amount']
                    target_tax_details_by_tax[tax.id][1] -= tax_data['tax_amount_currency']

        # Round according the tax lines.
        for tax_id, _tax_amount in target_tax_details_by_tax.items():
            if tax_id in tax_details_by_tax:
                tax_details_by_tax[tax_id][-1]['tax_amount'] += target_tax_details_by_tax[tax_id][0]
                tax_details_by_tax[tax_id][-1]['tax_amount_currency'] += target_tax_details_by_tax[tax_id][1]

        # Compute the untaxed amounts.
        amount_untaxed = 0.0
        amount_untaxed_currency = 0.0
        for base_line, tax_details_results in to_process:
            amount_untaxed += comp_curr.round(tax_details_results['total_excluded'] / base_line['rate'])
            amount_untaxed_currency += currency.round(tax_details_results['total_excluded'])

        def grouping_key_generator(base_line, tax_data):
            return {'tax_group': tax_data['tax'].tax_group_id}

        global_tax_details = self._aggregate_taxes(to_process, company, grouping_key_generator=grouping_key_generator)
        tax_group_details_list = sorted(
            global_tax_details['tax_details'].values(),
            key=lambda x: (x['tax_group'].sequence, x['tax_group'].id),
        )

        subtotal_order = {}
        encountered_base_amounts = {amount_untaxed_currency}
        groups_by_subtotal = defaultdict(list)
        for tax_detail in tax_group_details_list:
            tax_group = tax_detail['tax_group']
            subtotal_title = tax_group.preceding_subtotal or _("Untaxed Amount")
            sequence = tax_group.sequence

            # Handle a manual edition of tax lines.
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if x['tax_repartition_line'].tax_id.tax_group_id == tax_group
                ]
                if matched_tax_lines:
                    tax_detail['tax_amount_currency'] = sum(x['tax_amount_currency'] for x in matched_tax_lines)
                    tax_detail['tax_amount'] = sum(x['tax_amount'] for x in matched_tax_lines)

            # Manage order of subtotals.
            if subtotal_title not in subtotal_order:
                subtotal_order[subtotal_title] = sequence

            # Create the values for a single tax group.
            groups_by_subtotal[subtotal_title].append({
                'group_key': tax_group.id,
                'tax_group_id': tax_group.id,
                'tax_group_name': tax_group.name,
                'tax_group_label': tax_group.pos_receipt_label,
                'tax_group_amount': tax_detail['tax_amount_currency'],
                'tax_group_amount_company_currency': tax_detail['tax_amount'],
                'tax_group_base_amount': currency.round(tax_detail['display_base_amount_currency']),
                'tax_group_base_amount_company_currency': company.currency_id.round(tax_detail['display_base_amount']),
                'formatted_tax_group_amount': formatLang(self.env, tax_detail['tax_amount_currency'], currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(self.env, tax_detail['display_base_amount_currency'], currency_obj=currency),
                'display_formatted_tax_group_base_amount': not all(x['tax'].amount_type == 'fixed' for x in tax_detail['group_tax_details']),
            })
            encountered_base_amounts.add(currency.round(tax_detail['display_base_amount_currency']))

        # Compute amounts.
        subtotals = []
        subtotals_order = sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k])
        amount_total_currency = amount_untaxed_currency
        amount_total = amount_untaxed
        for subtotal_title in subtotals_order:
            subtotals.append({
                'name': subtotal_title,
                'amount': amount_total_currency,
                'amount_company_currency': amount_total,
                'formatted_amount': formatLang(self.env, amount_total_currency, currency_obj=currency),
            })
            amount_total_currency += sum(x['tax_group_amount'] for x in groups_by_subtotal[subtotal_title])
            amount_total += sum(x['tax_group_amount_company_currency'] for x in groups_by_subtotal[subtotal_title])

        results = {
            'amount_untaxed': currency.round(amount_untaxed_currency),
            'amount_total': currency.round(amount_total_currency),
            'formatted_amount_total': formatLang(self.env, amount_total_currency, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(self.env, amount_untaxed_currency, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': subtotals_order,
            'display_tax_base': len(encountered_base_amounts) != 1 or len(groups_by_subtotal) > 1,
        }
        if currency != comp_curr:
            results['amount_total_company_currency'] = comp_curr.round(amount_total)
        return results

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

    @api.model
    def _dispatch_negative_lines(self, base_lines, sorting_criteria=None, additional_dispatching_method=None):
        """
        This method tries to dispatch the amount of negative lines on positive ones with the same tax, resulting in
        a discount for these positive lines.

        :param base_lines: A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param sorting_criteria: Optional list of criteria to sort the candidate for a negative line
        :param additional_dispatching_method: Optional method to transfer additional information (like tax amounts).
                                              It takes as arguments:
                                                  - neg_base_line: the negative line being dispatched
                                                  - candidate: the positive line that will get discounted by neg_base_line
                                                  - discount_to_distribute: the amount being transferred
                                                  - is_zero: if the neg_base_line is nulled by the candidate

        :return: A dictionary in the following form:
            {
                'result_lines': Remaining list of positive lines, with their potential increased discount
                'orphan_negative_lines': A list of remaining negative lines that failed to be distributed
                'nulled_candidate_lines': list of previously positive lines that have been nulled (with the discount)
            }
        """
        results = {
            'result_lines': [],
            'orphan_negative_lines': [],
            'nulled_candidate_lines': [],
        }
        for line in base_lines:
            line['discount_amount'] = line['discount_amount_before_dispatching']

            if line['currency'].compare_amounts(line['gross_price_subtotal'], 0) < 0.0:
                results['orphan_negative_lines'].append(line)
            else:
                results['result_lines'].append(line)

        for neg_base_line in list(results['orphan_negative_lines']):
            candidates = [
                candidate
                for candidate in results['result_lines']
                if (
                    neg_base_line['currency'] == candidate['currency']
                    and neg_base_line['partner'] == candidate['partner']
                    and neg_base_line['taxes'] == candidate['taxes']
                )
            ]

            sorting_criteria = sorting_criteria or self._get_negative_lines_sorting_candidate_criteria()
            sorted_candidates = sorted(candidates, key=lambda candidate: tuple(method(candidate, neg_base_line) for method in sorting_criteria))

            # Dispatch.
            for candidate in sorted_candidates:
                net_price_subtotal = neg_base_line['gross_price_subtotal'] - neg_base_line['discount_amount']
                other_net_price_subtotal = candidate['gross_price_subtotal'] - candidate['discount_amount']
                discount_to_distribute = min(other_net_price_subtotal, -net_price_subtotal)

                candidate['discount_amount'] += discount_to_distribute
                neg_base_line['discount_amount'] -= discount_to_distribute

                remaining_to_distribute = neg_base_line['gross_price_subtotal'] - neg_base_line['discount_amount']
                is_zero = neg_base_line['currency'].is_zero(remaining_to_distribute)

                if additional_dispatching_method:
                    additional_dispatching_method(neg_base_line=neg_base_line, candidate=candidate, discount_to_distribute=discount_to_distribute, is_zero=is_zero)

                # Check if there is something left on the other line.
                remaining_amount = candidate['discount_amount'] - candidate['gross_price_subtotal']
                if candidate['currency'].is_zero(remaining_amount):
                    results['result_lines'].remove(candidate)
                    results['nulled_candidate_lines'].append(candidate)

                if is_zero:
                    results['orphan_negative_lines'].remove(neg_base_line)
                    break

        return results

    @api.model
    def _get_negative_lines_sorting_candidate_criteria(self):
        # Ordering by priority:
        # - same product
        # - same amount
        # - biggest amount
        def same_product(candidate, negative_line):
            return (
                not candidate['product']
                or not negative_line['product']
                or candidate['product'] != negative_line['product']
            )

        def same_price_subtotal(candidate, negative_line):
            return candidate['currency'].compare_amounts(candidate['price_subtotal'], -negative_line['price_subtotal']) != 0

        def biggest_amount(candidate, negative_line):
            return -candidate['price_subtotal']

        return [same_product, same_price_subtotal, biggest_amount]


class AccountTaxRepartitionLine(models.Model):
    _name = "account.tax.repartition.line"
    _description = "Tax Repartition Line"
    _order = 'document_type, repartition_type, sequence, id'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    factor_percent = fields.Float(
        string="%",
        default=100,
        required=True,
        help="Factor to apply on the account move lines generated from this distribution line, in percents",
    )
    factor = fields.Float(string="Factor Ratio", compute="_compute_factor", help="Factor to apply on the account move lines generated from this distribution line")
    repartition_type = fields.Selection(string="Based On", selection=[('base', 'Base'), ('tax', 'of tax')], required=True, default='tax', help="Base on which the factor will be applied.")
    document_type = fields.Selection(string="Related to", selection=[('invoice', 'Invoice'), ('refund', 'Refund')], required=True)
    account_id = fields.Many2one(string="Account",
        comodel_name='account.account',
        domain="[('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable', 'liability_payable', 'off_balance'))]",
        check_company=True,
        help="Account on which to post the tax amount")
    tag_ids = fields.Many2many(string="Tax Grids", comodel_name='account.account.tag', domain=[('applicability', '=', 'taxes')], copy=True, ondelete='restrict')
    tax_id = fields.Many2one(comodel_name='account.tax', ondelete='cascade', check_company=True)
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
        if not force_caba_exigibility and self.tax_id.tax_exigibility == 'on_payment' and not self._context.get('caba_no_transition_account'):
            return self.tax_id.cash_basis_transition_account_id
        else:
            return self.account_id
