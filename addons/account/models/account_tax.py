# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import clean_context, formatLang
from odoo.tools import frozendict, groupby, split_every

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
    )

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
        selection=[('group', 'Group of Taxes'), ('fixed', 'Fixed'), ('percent', 'Percentage of Price'), ('division', 'Percentage of Price Tax Included')],
        help="""
    - Group of Taxes: The tax is a set of sub taxes.
    - Fixed: The tax amount stays the same whatever the price.
    - Percentage of Price: The tax amount is a % of the price:
        e.g 100 * (1 + 10%) = 110 (not price included)
        e.g 110 / (1 + 10%) = 100 (price included)
    - Percentage of Price Tax Included: The tax amount is a division of the price:
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
    description = fields.Char(string='Description', translate=True)
    invoice_label = fields.Char(string='Label on Invoices', translate=True)
    price_include = fields.Boolean(string='Included in Price', default=False, tracking=True,
        help="Check this if the price you use on the product and invoices includes this tax.")
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
            (line, _('Removed'), old_line_values_dict[line]) if line in old_line_values_dict else (line, _('New'), new_line_values_dict[line])
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
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        if operator in ("ilike", "like"):
            name = AccountTax._parse_name_search(name)
        return super()._name_search(name, domain, operator, limit, order)

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
            if not tax._check_m2m_recursion('children_tax_ids'):
                raise ValidationError(_("Recursion found for tax %r.", tax.name))
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
            if self.env['account.move.line'].search([
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

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (Copy)", self.name)
        return super(AccountTax, self).copy(default=default)

    @api.depends('type_tax_use', 'tax_scope')
    @api.depends_context('append_type_to_tax_name')
    def _compute_display_name(self):
        type_tax_use = dict(self._fields['type_tax_use']._description_selection(self.env))
        tax_scope = dict(self._fields['tax_scope']._description_selection(self.env))
        for record in self:
            name = record.name
            if self._context.get('append_type_to_tax_name'):
                name += ' (%s)' % type_tax_use.get(record.type_tax_use)
            if record.tax_scope:
                name += ' (%s)' % tax_scope.get(record.tax_scope)
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

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None, fixed_multiplicator=1):
        """ Returns the amount of a single tax. base_amount is the actual amount on which the tax is applied, which is
            price_unit * quantity eventually affected by previous taxes (if tax is include_base_amount XOR price_include)
        """
        self.ensure_one()

        if self.amount_type == 'fixed':
            # Use copysign to take into account the sign of the base amount which includes the sign
            # of the quantity and the sign of the price_unit
            # Amount is the fixed price for the tax, it can be negative
            # Base amount included the sign of the quantity and the sign of the unit price and when
            # a product is returned, it can be done either by changing the sign of quantity or by changing the
            # sign of the price unit.
            # When the price unit is equal to 0, the sign of the quantity is absorbed in base_amount then
            # a "else" case is needed.
            if base_amount:
                return math.copysign(quantity, base_amount) * self.amount * abs(fixed_multiplicator)
            else:
                return quantity * self.amount * abs(fixed_multiplicator)

        price_include = self._context.get('force_price_include', self.price_include)

        # base * (1 + tax_amount) = new_base
        if self.amount_type == 'percent' and not price_include:
            return base_amount * self.amount / 100
        # <=> new_base = base / (1 + tax_amount)
        if self.amount_type == 'percent' and price_include:
            return base_amount - (base_amount / (1 + self.amount / 100))
        # base / (1 - tax_amount) = new_base
        if self.amount_type == 'division' and not price_include:
            return base_amount / (1 - self.amount / 100) - base_amount if (1 - self.amount / 100) else 0.0
        # <=> new_base * (1 - tax_amount) = base
        if self.amount_type == 'division' and price_include:
            return base_amount - (base_amount * (self.amount / 100))
        # default value for custom amount_type
        return 0.0

    def json_friendly_compute_all(self, price_unit, currency_id=None, quantity=1.0, product_id=None, partner_id=None, is_refund=False, include_caba_tags=False):
        """ Called by the reconciliation to compute taxes on writeoff during bank reconciliation
        """
        if currency_id:
            currency_id = self.env['res.currency'].browse(currency_id)
        if product_id:
            product_id = self.env['product.product'].browse(product_id)
        if partner_id:
            partner_id = self.env['res.partner'].browse(partner_id)

        # We first need to find out whether this tax computation is made for a refund
        tax_type = self and self[0].type_tax_use
        is_refund = is_refund or (tax_type == 'sale' and price_unit > 0) or (tax_type == 'purchase' and price_unit < 0)

        rslt = self.with_context(caba_no_transition_account=True)\
                   .compute_all(price_unit, currency=currency_id, quantity=quantity, product=product_id, partner=partner_id, is_refund=is_refund, include_caba_tags=include_caba_tags)

        return rslt

    def flatten_taxes_hierarchy(self, create_map=False):
        # Flattens the taxes contained in this recordset, returning all the
        # children at the bottom of the hierarchy, in a recordset, ordered by sequence.
        #   Eg. considering letters as taxes and alphabetic order as sequence :
        #   [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]
        # If create_map is True, an additional value is returned, a dictionary
        # mapping each child tax to its parent group
        all_taxes = self.env['account.tax']
        groups_map = {}
        for tax in self.sorted(key=lambda r: (r.sequence, r._origin.id)):
            if tax.amount_type == 'group':
                flattened_children = tax.children_tax_ids.flatten_taxes_hierarchy()
                all_taxes += flattened_children
                for flat_child in flattened_children:
                    groups_map[flat_child] = tax
            else:
                all_taxes += tax

        if create_map:
            return all_taxes, groups_map

        return all_taxes

    def get_tax_tags(self, is_refund, repartition_type):
        return self.repartition_line_ids.filtered(lambda x: (
            x.repartition_type == repartition_type
            and x.document_type == ('refund' if is_refund else 'invoice')
        )).mapped('tag_ids')

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True, include_caba_tags=False, fixed_multiplicator=1):
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
        :param fixed_multiplicator: The amount to multiply fixed amount taxes by.
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

        # 1) Flatten the taxes.
        taxes, groups_map = self.flatten_taxes_hierarchy(create_map=True)

        # 2) Deal with the rounding methods
        if not currency:
            currency = company.currency_id

        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        prec = currency.rounding

        # In some cases, it is necessary to force/prevent the rounding of the tax and the total
        # amounts. For example, in SO/PO line, we don't want to round the price unit at the
        # precision of the currency.
        # The context key 'round' allows to force the standard behavior.
        round_tax = False if company.tax_calculation_rounding_method == 'round_globally' else True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])

        if not round_tax:
            prec *= 1e-5

        # 3) Iterate the taxes in the reversed sequence order to retrieve the initial base of the computation.
        #     tax  |  base  |  amount  |
        # /\ ----------------------------
        # || tax_1 |  XXXX  |          | <- we are looking for that, it's the total_excluded
        # || tax_2 |   ..   |          |
        # || tax_3 |   ..   |          |
        # ||  ...  |   ..   |    ..    |
        #    ----------------------------
        def recompute_base(base_amount, incl_tax_amounts):
            """ Recompute the new base amount based on included fixed/percent amounts and the current base amount. """
            fixed_amount = incl_tax_amounts['fixed_amount']
            division_amount = sum(tax_factor for _i, tax_factor in incl_tax_amounts['division_taxes'])
            percent_amount = sum(tax_amount * sum_repartition_factor for _i, tax_amount, sum_repartition_factor in incl_tax_amounts['percent_taxes'])

            if company.country_code == 'IN':
                # For the indian case, when facing two percent price-included taxes having the same percentage,
                # both need to produce the same tax amounts. To do that, the tax amount of those taxes are computed
                # directly during the first traveling in reversed order.
                total_tax_amount = 0.0
                for i, tax_amount, sum_repartition_factor in incl_tax_amounts['percent_taxes']:
                    gross_tax_amount = float_round(base * tax_amount / (100 + percent_amount), precision_rounding=prec)
                    factored_tax_amount = float_round(gross_tax_amount * sum_repartition_factor, precision_rounding=prec)
                    total_tax_amount += factored_tax_amount
                    cached_tax_amounts[i] = gross_tax_amount
                    fixed_amount += factored_tax_amount
                for i, _tax_amount, _sum_repartition_factor in incl_tax_amounts['percent_taxes']:
                    cached_base_amounts[i] = base - total_tax_amount
                percent_amount = 0.0

            incl_tax_amounts.update({
                'percent_taxes': [],
                'division_taxes': [],
                'fixed_amount': 0.0,
            })

            return (base_amount - fixed_amount) / (1.0 + percent_amount / 100.0) * (100 - division_amount) / 100

        # The first/last base must absolutely be rounded to work in round globally.
        # Indeed, the sum of all taxes ('taxes' key in the result dictionary) must be strictly equals to
        # 'price_included' - 'price_excluded' whatever the rounding method.
        #
        # Example using the global rounding without any decimals:
        # Suppose two invoice lines: 27000 and 10920, both having a 19% price included tax.
        #
        #                   Line 1                      Line 2
        # -----------------------------------------------------------------------
        # total_included:   27000                       10920
        # tax:              27000 / 1.19 = 4310.924     10920 / 1.19 = 1743.529
        # total_excluded:   22689.076                   9176.471
        #
        # If the rounding of the total_excluded isn't made at the end, it could lead to some rounding issues
        # when summing the tax amounts, e.g. on invoices.
        # In that case:
        #  - amount_untaxed will be 22689 + 9176 = 31865
        #  - amount_tax will be 4310.924 + 1743.529 = 6054.453 ~ 6054
        #  - amount_total will be 31865 + 6054 = 37919 != 37920 = 27000 + 10920
        #
        # By performing a rounding at the end to compute the price_excluded amount, the amount_tax will be strictly
        # equals to 'price_included' - 'price_excluded' after rounding and then:
        #   Line 1: sum(taxes) = 27000 - 22689 = 4311
        #   Line 2: sum(taxes) = 10920 - 2176 = 8744
        #   amount_tax = 4311 + 8744 = 13055
        #   amount_total = 31865 + 13055 = 37920
        base = price_unit * quantity
        if self._context.get('round_base', True):
            base = currency.round(base)

        # For the computation of move lines, we could have a negative base value.
        # In this case, compute all with positive values and negate them at the end.
        sign = 1
        if currency.is_zero(base):
            sign = -1 if fixed_multiplicator < 0 else 1
        elif base < 0:
            sign = -1
            base = -base

        # Store the totals to reach when using price_include taxes (only the last price included in row)
        total_included_checkpoints = {}
        i = len(taxes) - 1
        store_included_tax_total = True
        # Keep track of the accumulated included fixed/percent amount.
        incl_tax_amounts = {
            'percent_taxes': [],
            'division_taxes': [],
            'fixed_amount': 0.0,
        }
        custom_fixed_amount_after = 0.0
        # Store the tax amounts we compute while searching for the total_excluded
        cached_base_amounts = {}
        cached_tax_amounts = {}
        is_base_affected = True
        if handle_price_include:
            for tax in reversed(taxes):
                tax_repartition_lines = (
                    is_refund
                    and tax.refund_repartition_line_ids
                    or tax.invoice_repartition_line_ids
                ).filtered(lambda x: x.repartition_type == "tax")
                sum_repartition_factor = sum(tax_repartition_lines.mapped("factor"))

                if tax.include_base_amount and is_base_affected:
                    base = recompute_base(base, incl_tax_amounts)
                    store_included_tax_total = True
                if self._context.get('force_price_include', tax.price_include):
                    if tax.amount_type == 'percent':
                        incl_tax_amounts['percent_taxes'].append((i, tax.amount, sum_repartition_factor))
                    elif tax.amount_type == 'division':
                        incl_tax_amounts['division_taxes'].append((i, tax.amount * sum_repartition_factor))
                    elif tax.amount_type == 'fixed':
                        incl_tax_amounts['fixed_amount'] = abs(quantity) * tax.amount * sum_repartition_factor * abs(fixed_multiplicator)
                    else:
                        # tax.amount_type == other (python)
                        tax_amount = tax._compute_amount(base, sign * price_unit, quantity, product, partner, fixed_multiplicator)
                        tax_amount = float_round(tax_amount, precision_rounding=prec)
                        incl_tax_amounts['fixed_amount'] += tax_amount
                        # Avoid unecessary re-computation
                        cached_tax_amounts[i] = tax_amount
                        custom_fixed_amount_after += tax_amount
                    # In case of a zero tax, do not store the base amount since the tax amount will
                    # be zero anyway. Group and Python taxes have an amount of zero, so do not take
                    # them into account.
                    if (
                        store_included_tax_total
                        and (tax.amount or tax.amount_type not in ("percent", "division", "fixed"))
                        and i not in cached_tax_amounts
                    ):
                        total_included_checkpoints[i] = base - custom_fixed_amount_after
                        store_included_tax_total = False
                        custom_fixed_amount_after = 0.0
                i -= 1
                is_base_affected = tax.is_base_affected

        total_excluded = recompute_base(base, incl_tax_amounts)
        if self._context.get('round_base', True):
            total_excluded = currency.round(total_excluded)

        # 4) Iterate the taxes in the sequence order to compute missing tax amounts.
        # Start the computation of accumulated amounts at the total_excluded value.
        base = total_included = total_void = total_excluded

        # Flag indicating the checkpoint used in price_include to avoid rounding issue must be skipped since the base
        # amount has changed because we are currently mixing price-included and price-excluded include_base_amount
        # taxes.
        skip_checkpoint = False

        # Get product tags, account.account.tag objects that need to be injected in all
        # the tax_tag_ids of all the move lines created by the compute all for this product.
        product_tag_ids = product.sudo().account_tag_ids.ids if product else []

        taxes_vals = []
        i = 0
        cumulated_tax_included_amount = 0
        for tax in taxes:
            price_include = self._context.get('force_price_include', tax.price_include)

            if price_include and i in cached_base_amounts:
                tax_base_amount = cached_base_amounts[i]
            elif price_include or tax.is_base_affected:
                tax_base_amount = base
            else:
                tax_base_amount = total_excluded

            tax_repartition_lines = (is_refund and tax.refund_repartition_line_ids or tax.invoice_repartition_line_ids).filtered(lambda x: x.repartition_type == 'tax')
            sum_repartition_factor = sum(tax_repartition_lines.mapped('factor'))

            #compute the tax_amount
            if price_include and i in cached_tax_amounts:
                tax_amount = cached_tax_amounts[i]
            elif not skip_checkpoint and price_include and total_included_checkpoints.get(i) is not None and sum_repartition_factor != 0:
                # We know the total to reach for that tax, so we make a substraction to avoid any rounding issues
                tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount)
                cumulated_tax_included_amount = 0
            else:
                tax_amount = tax.with_context(force_price_include=False)._compute_amount(
                    tax_base_amount, sign * price_unit, quantity, product, partner, fixed_multiplicator)

            # Round the tax_amount multiplied by the computed repartition lines factor.
            tax_amount = float_round(tax_amount, precision_rounding=prec)
            factorized_tax_amount = float_round(tax_amount * sum_repartition_factor, precision_rounding=prec)

            if price_include and total_included_checkpoints.get(i) is None:
                cumulated_tax_included_amount += factorized_tax_amount

            # If the tax affects the base of subsequent taxes, its tax move lines must
            # receive the base tags and tag_ids of these taxes, so that the tax report computes
            # the right total
            subsequent_taxes = self.env['account.tax']
            subsequent_tags = self.env['account.account.tag']
            if tax.include_base_amount:
                subsequent_taxes = taxes[i+1:].filtered('is_base_affected')

                taxes_for_subsequent_tags = subsequent_taxes

                if not include_caba_tags:
                    taxes_for_subsequent_tags = subsequent_taxes.filtered(lambda x: x.tax_exigibility != 'on_payment')

                subsequent_tags = taxes_for_subsequent_tags.get_tax_tags(is_refund, 'base')

            # Compute the tax line amounts by multiplying each factor with the tax amount.
            # Then, spread the tax rounding to ensure the consistency of each line independently with the factorized
            # amount. E.g:
            #
            # Suppose a tax having 4 x 50% repartition line applied on a tax amount of 0.03 with 2 decimal places.
            # The factorized_tax_amount will be 0.06 (200% x 0.03). However, each line taken independently will compute
            # 50% * 0.03 = 0.01 with rounding. It means there is 0.06 - 0.04 = 0.02 as total_rounding_error to dispatch
            # in lines as 2 x 0.01.
            repartition_line_amounts = [float_round(tax_amount * line.factor, precision_rounding=prec) for line in tax_repartition_lines]
            total_rounding_error = float_round(factorized_tax_amount - sum(repartition_line_amounts), precision_rounding=prec)
            nber_rounding_steps = int(abs(total_rounding_error / currency.rounding))
            rounding_error = float_round(nber_rounding_steps and total_rounding_error / nber_rounding_steps or 0.0, precision_rounding=prec)

            for repartition_line, line_amount in zip(tax_repartition_lines, repartition_line_amounts):

                if nber_rounding_steps:
                    line_amount += rounding_error
                    nber_rounding_steps -= 1

                if not include_caba_tags and tax.tax_exigibility == 'on_payment':
                    repartition_line_tags = self.env['account.account.tag']
                else:
                    repartition_line_tags = repartition_line.tag_ids

                taxes_vals.append({
                    'id': tax.id,
                    'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
                    'amount': sign * line_amount,
                    'base': float_round(sign * tax_base_amount, precision_rounding=prec),
                    'sequence': tax.sequence,
                    'account_id': repartition_line._get_aml_target_tax_account(force_caba_exigibility=include_caba_tags).id,
                    'analytic': tax.analytic,
                    'use_in_tax_closing': repartition_line.use_in_tax_closing,
                    'price_include': price_include,
                    'tax_exigibility': tax.tax_exigibility,
                    'tax_repartition_line_id': repartition_line.id,
                    'group': groups_map.get(tax),
                    'tag_ids': (repartition_line_tags + subsequent_tags).ids + product_tag_ids,
                    'tax_ids': subsequent_taxes.ids,
                })

                if not repartition_line.account_id:
                    total_void += line_amount

            # Affect subsequent taxes
            if tax.include_base_amount:
                base += factorized_tax_amount
                if not price_include:
                    skip_checkpoint = True

            total_included += factorized_tax_amount
            i += 1

        base_taxes_for_tags = taxes
        if not include_caba_tags:
            base_taxes_for_tags = base_taxes_for_tags.filtered(lambda x: x.tax_exigibility != 'on_payment')

        base_rep_lines = base_taxes_for_tags.mapped(is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids').filtered(lambda x: x.repartition_type == 'base')

        return {
            'base_tags': base_rep_lines.tag_ids.ids + product_tag_ids,
            'taxes': taxes_vals,
            'total_excluded': sign * total_excluded,
            'total_included': sign * currency.round(total_included),
            'total_void': sign * total_void,
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
            group_tax=None, account=None, analytic_distribution=None, tax_amount=None,
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
        tax_account = tax_repartition_line._get_aml_target_tax_account(force_caba_exigibility=force_caba_exigibility) or line_vals['account']
        return {
            'account_id': tax_account.id,
            'currency_id': line_vals['currency'].id,
            'partner_id': line_vals['partner'].id,
            'tax_repartition_line_id': tax_repartition_line.id,
            'tax_ids': [Command.set(tax_vals['tax_ids'])],
            'tax_tag_ids': [Command.set(tax_vals['tag_ids'])],
            'tax_id': tax_vals['group'].id if tax_vals['group'] else tax_vals['id'],
            'analytic_distribution': line_vals['analytic_distribution'] if tax_vals['analytic'] else {},
            '_extra_grouping_key_': line_vals.get('extra_context', {}).get('_extra_grouping_key_'),
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
            '_extra_grouping_key_': line_vals.get('extra_context', {}).get('_extra_grouping_key_'),
        }

    @api.model
    def _compute_taxes_for_single_line(self, base_line, handle_price_include=True, include_caba_tags=False, early_pay_discount_computation=None, early_pay_discount_percentage=None):
        orig_price_unit_after_discount = base_line['price_unit'] * (1 - (base_line['discount'] / 100.0))
        price_unit_after_discount = orig_price_unit_after_discount
        taxes = base_line['taxes']._origin
        currency = base_line['currency'] or self.env.company.currency_id
        rate = base_line['rate']

        if early_pay_discount_computation in ('included', 'excluded'):
            remaining_part_to_consider = (100 - early_pay_discount_percentage) / 100.0
            price_unit_after_discount = remaining_part_to_consider * price_unit_after_discount

        if taxes:
            taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                price_unit_after_discount,
                currency=currency,
                quantity=base_line['quantity'],
                product=base_line['product'],
                partner=base_line['partner'],
                is_refund=base_line['is_refund'],
                handle_price_include=base_line['handle_price_include'],
                include_caba_tags=include_caba_tags,
            )

            to_update_vals = {
                'tax_tag_ids': [Command.set(taxes_res['base_tags'])],
                'price_subtotal': taxes_res['total_excluded'],
                'price_total': taxes_res['total_included'],
            }

            if early_pay_discount_computation == 'excluded':
                new_taxes_res = taxes.with_context(**base_line['extra_context']).compute_all(
                    orig_price_unit_after_discount,
                    currency=currency,
                    quantity=base_line['quantity'],
                    product=base_line['product'],
                    partner=base_line['partner'],
                    is_refund=base_line['is_refund'],
                    handle_price_include=base_line['handle_price_include'],
                    include_caba_tags=include_caba_tags,
                )
                for tax_res, new_taxes_res in zip(taxes_res['taxes'], new_taxes_res['taxes']):
                    delta_tax = new_taxes_res['amount'] - tax_res['amount']
                    tax_res['amount'] += delta_tax
                    to_update_vals['price_total'] += delta_tax

            tax_values_list = []
            for tax_res in taxes_res['taxes']:
                tax_amount = tax_res['amount'] / rate
                if self.company_id.tax_calculation_rounding_method == 'round_per_line':
                    tax_amount = currency.round(tax_amount)
                tax_rep = self.env['account.tax.repartition.line'].browse(tax_res['tax_repartition_line_id'])
                tax_values_list.append({
                    **tax_res,
                    'tax_repartition_line': tax_rep,
                    'base_amount_currency': tax_res['base'],
                    'base_amount': currency.round(tax_res['base'] / rate),
                    'tax_amount_currency': tax_res['amount'],
                    'tax_amount': tax_amount,
                })

        else:
            price_subtotal = currency.round(price_unit_after_discount * base_line['quantity'])
            to_update_vals = {
                'tax_tag_ids': [Command.clear()],
                'price_subtotal': price_subtotal,
                'price_total': price_subtotal,
            }
            tax_values_list = []

        return to_update_vals, tax_values_list

    @api.model
    def _aggregate_taxes(self, to_process, filter_tax_values_to_apply=None, grouping_key_generator=None, distribute_total_on_line=True):

        def default_grouping_key_generator(base_line, tax_values):
            return {'tax': tax_values['tax_repartition_line'].tax_id}

        global_tax_details = {
            'to_process': to_process,
            'base_amount_currency': 0.0,
            'base_amount': 0.0,
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
            'tax_details': defaultdict(lambda: {
                'base_amount_currency': 0.0,
                'base_amount': 0.0,
                'tax_amount_currency': 0.0,
                'tax_amount': 0.0,
                'group_tax_details': [],
                'records': set(),
            }),
            'tax_details_per_record': defaultdict(lambda: {
                'base_amount_currency': 0.0,
                'base_amount': 0.0,
                'tax_amount_currency': 0.0,
                'tax_amount': 0.0,
                'tax_details': defaultdict(lambda: {
                    'base_amount_currency': 0.0,
                    'base_amount': 0.0,
                    'tax_amount_currency': 0.0,
                    'tax_amount': 0.0,
                    'group_tax_details': [],
                    'records': set(),
                }),
            }),
        }

        def add_tax_values(record, results, grouping_key, serialized_grouping_key, tax_values):
            # Add to global results.
            results['tax_amount_currency'] += tax_values['tax_amount_currency']
            results['tax_amount'] += tax_values['tax_amount']

            # Add to tax details.
            if serialized_grouping_key not in results['tax_details']:
                tax_details = results['tax_details'][serialized_grouping_key]
                tax_details.update(grouping_key)
                tax_details['base_amount_currency'] = tax_values['base_amount_currency']
                tax_details['base_amount'] = tax_values['base_amount']
                tax_details['records'].add(record)
            else:
                tax_details = results['tax_details'][serialized_grouping_key]
                if record not in tax_details['records']:
                    tax_details['base_amount_currency'] += tax_values['base_amount_currency']
                    tax_details['base_amount'] += tax_values['base_amount']
                    tax_details['records'].add(record)
            tax_details['tax_amount_currency'] += tax_values['tax_amount_currency']
            tax_details['tax_amount'] += tax_values['tax_amount']
            tax_details['group_tax_details'].append(tax_values)

        if self.env.company.tax_calculation_rounding_method == 'round_globally' and distribute_total_on_line:
            # Aggregate all amounts according the tax lines grouping key.
            comp_currency = self.env.company.currency_id
            amount_per_tax_repartition_line_id = defaultdict(lambda: {
                'tax_amount': 0.0,
                'tax_amount_currency': 0.0,
                'tax_values_list': [],
            })
            for base_line, to_update_vals, tax_values_list in to_process:
                currency = base_line['currency'] or comp_currency
                for tax_values in tax_values_list:
                    grouping_key = frozendict(self._get_generation_dict_from_base_line(base_line, tax_values))
                    total_amounts = amount_per_tax_repartition_line_id[grouping_key]
                    total_amounts['tax_amount_currency'] += tax_values['tax_amount_currency']
                    total_amounts['tax_amount'] += tax_values['tax_amount']
                    total_amounts['tax_values_list'].append(tax_values)

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
                    tax_values_list = values['tax_values_list']
                    nb_error = math.ceil(abs_diff / currency.rounding)
                    nb_cents_per_tax_values = math.floor(nb_error / len(tax_values_list))
                    nb_extra_cent = nb_error % len(tax_values_list)

                    for tax_values in tax_values_list:
                        if not abs_diff:
                            break

                        nb_amount_curr_cent = nb_cents_per_tax_values
                        if nb_extra_cent:
                            nb_amount_curr_cent += 1
                            nb_extra_cent -= 1

                        # We can have more than one cent to distribute on a single tax_values.
                        abs_delta_to_add = min(abs_diff, currency.rounding * nb_amount_curr_cent)
                        tax_values[amount_field] += diff_sign * abs_delta_to_add
                        abs_diff -= abs_delta_to_add

        grouping_key_generator = grouping_key_generator or default_grouping_key_generator

        for base_line, to_update_vals, tax_values_list in to_process:
            record = base_line['record']

            # Add to global tax amounts.
            global_tax_details['base_amount_currency'] += to_update_vals['price_subtotal']

            currency = base_line['currency'] or self.env.company.currency_id
            base_amount = currency.round(to_update_vals['price_subtotal'] / base_line['rate'])
            global_tax_details['base_amount'] += base_amount

            for tax_values in tax_values_list:
                if filter_tax_values_to_apply and not filter_tax_values_to_apply(base_line, tax_values):
                    continue

                grouping_key = grouping_key_generator(base_line, tax_values)
                serialized_grouping_key = frozendict(grouping_key)

                # Add to invoice line global tax amounts.
                if serialized_grouping_key not in global_tax_details['tax_details_per_record'][record]:
                    record_global_tax_details = global_tax_details['tax_details_per_record'][record]
                    record_global_tax_details['base_amount_currency'] = to_update_vals['price_subtotal']
                    record_global_tax_details['base_amount'] = base_amount
                else:
                    record_global_tax_details = global_tax_details['tax_details_per_record'][record]

                add_tax_values(record, global_tax_details, grouping_key, serialized_grouping_key, tax_values)
                add_tax_values(record, record_global_tax_details, grouping_key, serialized_grouping_key, tax_values)

        return global_tax_details

    @api.model
    def _compute_taxes(self, base_lines, tax_lines=None, handle_price_include=True, include_caba_tags=False):
        """ Generic method to compute the taxes for different business models.

        :param base_lines: A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param tax_lines: A list of python dictionaries created using the '_convert_to_tax_line_dict' method.
        :param handle_price_include:    Manage the price-included taxes. If None, use the 'handle_price_include' key
                                        set on base lines.
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

        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(
                base_line,
                include_caba_tags=include_caba_tags,
            )
            to_process.append((base_line, to_update_vals, tax_values_list))
            res['base_lines_to_update'].append((base_line, to_update_vals))
            currency = base_line['currency'] or self.env.company.currency_id
            res['totals'][currency]['amount_untaxed'] += to_update_vals['price_subtotal']

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

        def grouping_key_generator(base_line, tax_values):
            return self._get_generation_dict_from_base_line(base_line, tax_values, force_caba_exigibility=include_caba_tags)

        # Update/create the tax lines.
        global_tax_details = self._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        for grouping_key, tax_values in global_tax_details['tax_details'].items():
            if tax_values['currency_id']:
                currency = self.env['res.currency'].browse(tax_values['currency_id'])
                tax_amount = currency.round(tax_values['tax_amount_currency'])
                res['totals'][currency]['amount_tax'] += tax_amount

            if grouping_key in existing_tax_line_map:
                # Update an existing tax line.
                line_vals = existing_tax_line_map.pop(grouping_key)
                res['tax_lines_to_update'].append((line_vals, tax_values))
            else:
                # Create a new tax line.
                res['tax_lines_to_add'].append(tax_values)

        for line_vals in existing_tax_line_map.values():
            res['tax_lines_to_delete'].append(line_vals)

        return res

    @api.model
    def _prepare_tax_totals(self, base_lines, currency, tax_lines=None, is_company_currency_requested=False):
        """ Compute the tax totals details for the business documents.
        :param base_lines:                      A list of python dictionaries created using the '_convert_to_tax_base_line_dict' method.
        :param currency:                        The currency set on the business document.
        :param tax_lines:                       Optional list of python dictionaries created using the '_convert_to_tax_line_dict'
                                                method. If specified, the taxes will be recomputed using them instead of
                                                recomputing the taxes on the provided base lines.
        :param is_company_currency_requested :  Optional boolean which indicates whether or not the company currency is
                                                requested from the function. This can typically be used when using an
                                                invoice in foreign currency and the company currency is required.

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

        # ==== Compute the taxes ====

        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))

        def grouping_key_generator(base_line, tax_values):
            source_tax = tax_values['tax_repartition_line'].tax_id
            return {'tax_group': source_tax.tax_group_id}

        global_tax_details = self._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        tax_group_vals_list = []
        for tax_detail in global_tax_details['tax_details'].values():
            tax_group_vals = {
                'tax_group': tax_detail['tax_group'],
                'base_amount': tax_detail['base_amount_currency'],
                'tax_amount': tax_detail['tax_amount_currency'],
                'hide_base_amount': all(x['tax_repartition_line'].tax_id.amount_type == 'fixed' for x in tax_detail['group_tax_details']),
            }
            if is_company_currency_requested:
                tax_group_vals['base_amount_company_currency'] = tax_detail['base_amount']
                tax_group_vals['tax_amount_company_currency'] = tax_detail['tax_amount']

            # Handle a manual edition of tax lines.
            if tax_lines is not None:
                matched_tax_lines = [
                    x
                    for x in tax_lines
                    if x['tax_repartition_line'].tax_id.tax_group_id == tax_detail['tax_group']
                ]
                if matched_tax_lines:
                    tax_group_vals['tax_amount'] = sum(x['tax_amount'] for x in matched_tax_lines)

            tax_group_vals_list.append(tax_group_vals)

        tax_group_vals_list = sorted(tax_group_vals_list, key=lambda x: (x['tax_group'].sequence, x['tax_group'].id))

        # ==== Partition the tax group values by subtotals ====

        amount_untaxed = global_tax_details['base_amount_currency']
        amount_tax = 0.0

        amount_untaxed_company_currency = global_tax_details['base_amount']
        amount_tax_company_currency = 0.0

        subtotal_order = {}
        groups_by_subtotal = defaultdict(list)
        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals['tax_group']

            subtotal_title = tax_group.preceding_subtotal or _("Untaxed Amount")
            sequence = tax_group.sequence

            subtotal_order[subtotal_title] = min(subtotal_order.get(subtotal_title, float('inf')), sequence)
            groups_by_subtotal[subtotal_title].append({
                'group_key': tax_group.id,
                'tax_group_id': tax_group.id,
                'tax_group_name': tax_group.name,
                'tax_group_amount': tax_group_vals['tax_amount'],
                'tax_group_base_amount': tax_group_vals['base_amount'],
                'formatted_tax_group_amount': formatLang(self.env, tax_group_vals['tax_amount'], currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(self.env, tax_group_vals['base_amount'], currency_obj=currency),
                'hide_base_amount': tax_group_vals['hide_base_amount'],
            })
            if is_company_currency_requested:
                groups_by_subtotal[subtotal_title][-1]['tax_group_amount_company_currency'] = tax_group_vals['tax_amount_company_currency']
                groups_by_subtotal[subtotal_title][-1]['tax_group_base_amount_company_currency'] = tax_group_vals['base_amount_company_currency']

        # ==== Build the final result ====

        subtotals = []
        for subtotal_title in sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]):
            amount_total = amount_untaxed + amount_tax
            subtotals.append({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': formatLang(self.env, amount_total, currency_obj=currency),
            })
            if is_company_currency_requested:
                subtotals[-1]['amount_company_currency'] = amount_untaxed_company_currency + amount_tax_company_currency
                amount_tax_company_currency += sum(x['tax_group_amount_company_currency'] for x in groups_by_subtotal[subtotal_title])

            amount_tax += sum(x['tax_group_amount'] for x in groups_by_subtotal[subtotal_title])

        amount_total = amount_untaxed + amount_tax
        amount_total_company_currency = amount_untaxed_company_currency + amount_tax_company_currency

        display_tax_base = (len(global_tax_details['tax_details']) == 1 and currency.compare_amounts(tax_group_vals_list[0]['base_amount'], amount_untaxed) != 0)\
                           or len(global_tax_details['tax_details']) > 1

        result = {
            'amount_untaxed': currency.round(amount_untaxed) if currency else amount_untaxed,
            'amount_total': currency.round(amount_total) if currency else amount_total,
            'formatted_amount_total': formatLang(self.env, amount_total, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(self.env, amount_untaxed, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'subtotals_order': sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]),
            'display_tax_base': display_tax_base
        }
        if is_company_currency_requested:
            comp_currency = self.env.company.currency_id
            result['amount_total_company_currency'] = comp_currency.round(amount_total_company_currency)

        return result

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
