# -*- coding: utf-8 -*-

import math
import logging

from odoo.osv import expression
from odoo.tools.float_utils import float_round as round, float_compare
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _, tools

TYPE_TAX_USE = [
    ('sale', 'Sales'),
    ('purchase', 'Purchases'),
    ('none', 'None'),
]

_logger = logging.getLogger(__name__)


class AccountAccountType(models.Model):
    _name = "account.account.type"
    _description = "Account Type"

    name = fields.Char(string='Account Type', required=True, translate=True)
    include_initial_balance = fields.Boolean(string="Bring Accounts Balance Forward", help="Used in reports to know if we should consider journal items from the beginning of time instead of from the fiscal year only. Account types that should be reset to zero at each new fiscal year (like expenses, revenue..) should not have this option set.")
    type = fields.Selection([
        ('other', 'Regular'),
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('liquidity', 'Liquidity'),
    ], required=True, default='other',
        help="The 'Internal Type' is used for features available on "\
        "different types of accounts: liquidity type is for cash or bank accounts"\
        ", payable/receivable is for vendor/customer accounts.")
    internal_group = fields.Selection([
        ('equity', 'Equity'),
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('off_balance', 'Off Balance'),
    ], string="Internal Group",
        required=True,
        help="The 'Internal Group' is used to filter accounts based on the internal group set on the account type.")
    note = fields.Text(string='Description')


class AccountAccountTag(models.Model):
    _name = 'account.account.tag'
    _description = 'Account Tag'

    name = fields.Char('Tag Name', required=True)
    applicability = fields.Selection([('accounts', 'Accounts'), ('taxes', 'Taxes')], required=True, default='accounts')
    color = fields.Integer('Color Index')
    active = fields.Boolean(default=True, help="Set active to false to hide the Account Tag without removing it.")
    tax_report_line_ids = fields.Many2many(string="Tax Report Lines", comodel_name='account.tax.report.line', relation='account_tax_report_line_tags_rel', help="The tax report lines using this tag")
    tax_negate = fields.Boolean(string="Negate Tax Balance", help="Check this box to negate the absolute value of the balance of the lines associated with this tag in tax report computation.")
    country_id = fields.Many2one(string="Country", comodel_name='res.country', help="Country for which this tag is available, when applied on taxes.")

    @api.model
    def _get_tax_tags(self, tag_name, country_id):
        """ Returns all the tax tags corresponding to the tag name given in parameter
        in the specified country.
        """
        escaped_tag_name = tag_name.replace('\\', '\\\\').replace('%', '\%').replace('_', '\_')
        return self.env['account.account.tag'].search([('name', '=like', '_' + escaped_tag_name), ('country_id', '=', country_id), ('applicability', '=', 'taxes')])

    @api.constrains('country_id', 'applicability')
    def _validate_tag_country(self):
        for record in self:
            if record.applicability == 'taxes' and not record.country_id:
                raise ValidationError(_("A tag defined to be used on taxes must always have a country set."))


class AccountTaxReport(models.Model):
    _name = "account.tax.report"
    _description = 'Account Tax Report'
    _order = 'country_id, name'

    name = fields.Char(string="Name", required=True, help="Name of this tax report")
    country_id = fields.Many2one(string="Country", comodel_name='res.country', required=True, default=lambda x: x.env.company.country_id.id, help="Country for which this report is available.")
    line_ids = fields.One2many(string="Report Lines", comodel_name='account.tax.report.line', inverse_name='report_id', help="Content of this tax report")
    root_line_ids = fields.One2many(string="Root Report Lines", comodel_name='account.tax.report.line', inverse_name='report_id', domain=[('parent_id', '=', None)], help="Subset of line_ids, containing the lines at the root of the report.")

    def write(self, vals):
        # Overridden so that we change the country _id of the existing tags
        # when writing the country_id of the report, or create new tags
        # for the new country if the tags are shared with some other report.

        if 'country_id' in vals:
            tags_cache = {}
            for record in self.filtered(lambda x: x.country_id.id != vals['country_id']):
                for line in record.line_ids:
                    if line.tag_ids:
                        #The tags for this country may have been created by a previous line in this loop
                        cache_key = (vals['country_id'], line.tag_name)
                        if cache_key not in tags_cache:
                            tags_cache[cache_key] = self.env['account.account.tag']._get_tax_tags(line.tag_name, vals['country_id'])

                        new_tags = tags_cache[cache_key]

                        if new_tags:
                            tags_to_unlink = line.tag_ids.filtered(lambda x: record == x.mapped('tax_report_line_ids.report_id'))
                            # == instead of in, as we only want tags_to_unlink to contain the tags that are not linked to any other report than the one we're considering
                            line.write({'tag_ids': [(6, 0, new_tags.ids)]})
                            self.env['account.tax.report.line']._delete_tags_from_taxes(tags_to_unlink.ids)

                        elif line.mapped('tag_ids.tax_report_line_ids.report_id').filtered(lambda x: x not in self):
                            line.write({'tag_ids': [(5, 0, 0)] + line._get_tags_create_vals(line.tag_name, vals['country_id'])})
                            tags_cache[cache_key] = line.tag_ids

                        else:
                            line.tag_ids.write({'country_id': vals['country_id']})

        return super(AccountTaxReport, self).write(vals)

    def copy(self, default=None):
        # Overridden from regular copy, since the ORM does not manage
        # the copy of the lines hierarchy properly (all the parent_id fields
        # need to be reassigned to the corresponding copies).

        copy_default = {k:v for k, v in default.items() if k != 'line_ids'} if default else None
        copied_report = super(AccountTaxReport, self).copy(default=copy_default) #This copies the report without its lines

        lines_map = {} # maps original lines to their copies (using ids)
        for line in self.line_ids:
            copy = line.copy({'parent_id': lines_map.get(line.parent_id.id, None), 'report_id': copied_report.id})
            lines_map[line.id] = copy.id

        return copied_report

    def get_lines_in_hierarchy(self):
        """ Returns an interator to the lines of this tax report, were parent lines
        ar all directly followed by their children.
        """
        self.ensure_one()
        lines_to_treat = list(self.line_ids.filtered(lambda x: not x.parent_id)) # Used as a stack, whose index 0 is the top
        while lines_to_treat:
            to_yield = lines_to_treat[0]
            lines_to_treat = list(to_yield.children_line_ids) + lines_to_treat[1:]
            yield to_yield

    def get_checks_to_perform(self, d):
        """ To override in localizations
        If value is a float, it will be formatted with format_value
        The line is not displayed if it is falsy (0, 0.0, False, ...)
        :param d: the mapping dictionay between codes and values
        :return: iterable of tuple (name, value)
        """
        self.ensure_one()
        return []

    def validate_country_id(self):
        for record in self:
            if any(line.tag_ids.mapped('country_id') != record.country_id for line in record.line_ids):
                raise ValidationError(_("The tags associated with tax report line objects should all have the same country set as the tax report containing these lines."))


class AccountTaxReportLine(models.Model):
    _name = "account.tax.report.line"
    _description = 'Account Tax Report Line'
    _order = 'sequence'
    _parent_store = True

    name = fields.Char(string="Name", required=True, help="Complete name for this report line, to be used in report.")
    tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', relation='account_tax_report_line_tags_rel', help="Tax tags populating this line")
    report_action_id = fields.Many2one(string="Report Action", comodel_name='ir.actions.act_window', help="The optional action to call when clicking on this line in accounting reports.")
    children_line_ids = fields.One2many(string="Children Lines", comodel_name='account.tax.report.line', inverse_name='parent_id', help="Lines that should be rendered as children of this one")
    parent_id = fields.Many2one(string="Parent Line", comodel_name='account.tax.report.line')
    sequence = fields.Integer(string='Sequence', required=True,
        help="Sequence determining the order of the lines in the report (smaller ones come first). This order is applied locally per section (so, children of the same line are always rendered one after the other).")
    parent_path = fields.Char(index=True)
    report_id = fields.Many2one(string="Tax Report", required=True, comodel_name='account.tax.report', ondelete='cascade', help="The parent tax report of this line")

    #helper to create tags (positive and negative) on report line creation
    tag_name = fields.Char(string="Tag Name", help="Short name for the tax grid corresponding to this report line. Leave empty if this report line should not correspond to any such grid.")

    #fields used in specific localization reports, where a report line isn't simply the given by the sum of account.move.line with selected tags
    code = fields.Char(string="Code", help="Optional unique code to refer to this line in total formulas")
    formula = fields.Char(string="Formula", help="Python expression used to compute the value of a total line. This field is mutually exclusive with tag_name, setting it turns the line to a total line. Tax report line codes can be used as variables in this expression to refer to the balance of the corresponding lines in the report. A formula cannot refer to another line using a formula.")

    @api.model
    def create(self, vals):
        # Manage tags
        tag_name = vals.get('tag_name', '')
        if tag_name and vals.get('report_id'):
            report = self.env['account.tax.report'].browse(vals['report_id'])
            country = report.country_id

            existing_tags = self.env['account.account.tag']._get_tax_tags(tag_name, country.id)

            if existing_tags:
                # We connect the new report line to the already existing tags
                vals['tag_ids'] = [(6, 0, existing_tags.ids)]
            else:
                # We create new ones
                vals['tag_ids'] = self._get_tags_create_vals(tag_name, country.id)

        return super(AccountTaxReportLine, self).create(vals)

    @api.model
    def _get_tags_create_vals(self, tag_name, country_id):
        minus_tag_vals = {
          'name': '-' + tag_name,
          'applicability': 'taxes',
          'tax_negate': True,
          'country_id': country_id,
        }
        plus_tag_vals = {
          'name': '+' + tag_name,
          'applicability': 'taxes',
          'tax_negate': False,
          'country_id': country_id,
        }
        return [(0, 0, minus_tag_vals), (0, 0, plus_tag_vals)]

    def write(self, vals):
        tag_name_postponed = None

        # If tag_name was set, but not tag_ids, we postpone the write of
        # tag_name, and perform it only after having generated/retrieved the tags.
        # Otherwise, tag_name and tags' name would not match, breaking
        # _validate_tags constaint.
        postpone_tag_name = 'tag_name' in vals and not 'tag_ids' in vals

        if postpone_tag_name:
            tag_name_postponed = vals.pop('tag_name')

        rslt = super(AccountTaxReportLine, self).write(vals)

        if postpone_tag_name:
            # If tag_name modification has been postponed,
            # we need to search for existing tags corresponding to the new tag name
            # (or create them if they don't exist yet) and assign them to the records

            records_by_country = {}
            for record in self.filtered(lambda x: x.tag_name != tag_name_postponed):
                records_by_country[record.report_id.country_id.id] = records_by_country.get(record.report_id.country_id.id, self.env['account.tax.report.line']) + record

            for country_id, records in records_by_country.items():
                if tag_name_postponed:
                    record_tag_names = records.mapped('tag_name')
                    if len(record_tag_names) == 1 and record_tag_names[0]:
                        # If all the records already have the same tag_name before writing,
                        # we simply want to change the name of the existing tags
                        to_update = records.mapped('tag_ids.tax_report_line_ids')
                        tags_to_update = to_update.mapped('tag_ids')
                        minus_child_tags = tags_to_update.filtered(lambda x: x.tax_negate)
                        minus_child_tags.write({'name': '-' + tag_name_postponed})
                        plus_child_tags = tags_to_update.filtered(lambda x: not x.tax_negate)
                        plus_child_tags.write({'name': '+' + tag_name_postponed})
                        super(AccountTaxReportLine, to_update).write({'tag_name': tag_name_postponed})

                    else:
                        existing_tags = self.env['account.account.tag']._get_tax_tags(tag_name_postponed, country_id)
                        records_to_link = records
                        tags_to_remove = self.env['account.account.tag']

                        if not existing_tags and records_to_link:
                            # If the tag does not exist yet, we first create it by
                            # linking it to the first report line of the record set
                            first_record = records_to_link[0]
                            tags_to_remove += first_record.tag_ids
                            first_record.write({'tag_name': tag_name_postponed, 'tag_ids': [(5, 0, 0)] + self._get_tags_create_vals(tag_name_postponed, country_id)})
                            existing_tags = first_record.tag_ids
                            records_to_link -= first_record

                        # All the lines sharing their tags must always be synchronized,
                        tags_to_remove += records_to_link.mapped('tag_ids')
                        records_to_link = tags_to_remove.mapped('tax_report_line_ids')
                        self._delete_tags_from_taxes(tags_to_remove.ids)
                        records_to_link.write({'tag_name': tag_name_postponed, 'tag_ids': [(2, tag.id) for tag in tags_to_remove] + [(6, 0, existing_tags.ids)]})

                else:
                    # tag_name was set empty, so we remove the tags on current lines
                    # If some tags are still referenced by other report lines,
                    # we keep them ; else, we delete them from DB
                    line_tags = records.mapped('tag_ids')
                    other_lines_same_tag = line_tags.mapped('tax_report_line_ids').filtered(lambda x: x not in records)
                    if not other_lines_same_tag:
                        self._delete_tags_from_taxes(line_tags.ids)
                    orm_cmd_code = other_lines_same_tag and 3 or 2
                    records.write({'tag_name': None, 'tag_ids': [(orm_cmd_code, tag.id) for tag in line_tags]})

        return rslt

    def unlink(self):
        self._delete_tags_from_taxes(self.mapped('tag_ids.id'))
        children = self.mapped('children_line_ids')
        if children:
            children.unlink()
        return super(AccountTaxReportLine, self).unlink()

    @api.model
    def _delete_tags_from_taxes(self, tag_ids_to_delete):
        """ Based on a list of tag ids, removes them first from the
        repartition lines they are linked to, then deletes them
        from the account move lines.
        """
        if not tag_ids_to_delete:
            # Nothing to do, then!
            return

        self.env.cr.execute("""
            delete from account_account_tag_account_tax_repartition_line_rel
            where account_account_tag_id in %(tag_ids_to_delete)s;

            delete from account_account_tag_account_move_line_rel
            where account_account_tag_id in %(tag_ids_to_delete)s;
        """, {'tag_ids_to_delete': tuple(tag_ids_to_delete)})

        self.env['account.move.line'].invalidate_cache(fnames=['tax_tag_ids'])
        self.env['account.tax.repartition.line'].invalidate_cache(fnames=['tag_ids'])

    @api.constrains('formula', 'tag_name')
    def _validate_formula(self):
        for record in self:
            if record.formula and record.tag_name:
                raise ValidationError(_("Tag name and formula are mutually exclusive, they should not be set together on the same tax report line."))

    @api.constrains('tag_name', 'tag_ids')
    def _validate_tags(self):
        for record in self.filtered(lambda x: x.tag_ids):
            neg_tags = record.tag_ids.filtered(lambda x: x.tax_negate)
            pos_tags = record.tag_ids.filtered(lambda x: not x.tax_negate)

            if (len(neg_tags) != 1 or len(pos_tags) != 1):
                raise ValidationError(_("If tags are defined for a tax report line, only two are allowed on it: a positive and a negative one."))

            if neg_tags.name != '-'+record.tag_name or pos_tags.name != '+'+record.tag_name:
                raise ValidationError(_("The tags linked to a tax report line should always match its tag name."))

#----------------------------------------------------------
# Accounts
#----------------------------------------------------------


class AccountAccount(models.Model):
    _name = "account.account"
    _description = "Account"
    _order = "code, company_id"
    _check_company_auto = True

    @api.constrains('internal_type', 'reconcile')
    def _check_reconcile(self):
        for account in self:
            if account.internal_type in ('receivable', 'payable') and account.reconcile == False:
                raise ValidationError(_('You cannot have a receivable/payable account that is not reconcilable. (account code: %s)') % account.code)

    @api.constrains('user_type_id')
    def _check_user_type_id(self):
        data_unaffected_earnings = self.env.ref('account.data_unaffected_earnings')
        result = self.read_group([('user_type_id', '=', data_unaffected_earnings.id)], ['company_id'], ['company_id'])
        for res in result:
            if res.get('company_id_count', 0) >= 2:
                account_unaffected_earnings = self.search([('company_id', '=', res['company_id'][0]),
                                                           ('user_type_id', '=', data_unaffected_earnings.id)])
                raise ValidationError(_('You cannot have more than one account with "Current Year Earnings" as type. (accounts: %s)') % [a.code for a in account_unaffected_earnings])

    name = fields.Char(required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Account Currency',
        help="Forces all moves for this account to have this account currency.")
    code = fields.Char(size=64, required=True, index=True)
    deprecated = fields.Boolean(index=True, default=False)
    used = fields.Boolean(store=False, search='_search_used')
    user_type_id = fields.Many2one('account.account.type', string='Type', required=True,
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")
    internal_type = fields.Selection(related='user_type_id.type', string="Internal Type", store=True, readonly=True)
    internal_group = fields.Selection(related='user_type_id.internal_group', string="Internal Group", store=True, readonly=True)
    #has_unreconciled_entries = fields.Boolean(compute='_compute_has_unreconciled_entries',
    #    help="The account has at least one unreconciled debit and credit since last time the invoices & payments matching was performed.")
    reconcile = fields.Boolean(string='Allow Reconciliation', default=False,
        help="Check this box if this account allows invoices & payments matching of journal items.")
    tax_ids = fields.Many2many('account.tax', 'account_account_tax_default_rel',
        'account_id', 'tax_id', string='Default Taxes',
        check_company=True,
        context={'append_type_to_tax_name': True})
    note = fields.Text('Internal Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    tag_ids = fields.Many2many('account.account.tag', 'account_account_account_tag', string='Tags', help="Optional tags you may want to assign for custom reporting")
    group_id = fields.Many2one('account.group', compute='_compute_account_group', store=True)
    root_id = fields.Many2one('account.root', compute='_compute_account_root', store=True)
    allowed_journal_ids = fields.Many2many('account.journal', string="Allowed Journals", help="Define in which journals this account can be used. If empty, can be used in all journals.")

    opening_debit = fields.Monetary(string="Opening debit", compute='_compute_opening_debit_credit', inverse='_set_opening_debit', help="Opening debit value for this account.")
    opening_credit = fields.Monetary(string="Opening credit", compute='_compute_opening_debit_credit', inverse='_set_opening_credit', help="Opening credit value for this account.")

    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the account must be unique per company !')
    ]

    @api.constrains('reconcile', 'internal_group', 'tax_ids')
    def _constrains_reconcile(self):
        for record in self:
            if record.internal_group == 'off_balance':
                if record.reconcile:
                    raise UserError(_('An Off-Balance account can not be reconcilable'))
                if record.tax_ids:
                    raise UserError(_('An Off-Balance account can not have taxes'))

    @api.constrains('allowed_journal_ids')
    def _constrains_allowed_journal_ids(self):
        self.env['account.move.line'].flush(['account_id', 'journal_id'])
        self.flush(['allowed_journal_ids'])
        self._cr.execute("""
            SELECT aml.id
            FROM account_move_line aml
            WHERE aml.account_id in %s
            AND EXISTS (SELECT 1 FROM account_account_account_journal_rel WHERE account_account_id = aml.account_id)
            AND NOT EXISTS (SELECT 1 FROM account_account_account_journal_rel WHERE account_account_id = aml.account_id AND account_journal_id = aml.journal_id)
        """, [tuple(self.ids)])
        ids = self._cr.fetchall()
        if ids:
            raise ValidationError(_('Some journal items already exist with this account but in other journals than the allowed ones.'))

    @api.constrains('currency_id')
    def _check_journal_consistency(self):
        ''' Ensure the currency set on the journal is the same as the currency set on the
        linked accounts.
        '''
        if not self:
            return

        self.env['account.account'].flush(['currency_id'])
        self.env['account.journal'].flush([
            'currency_id',
            'default_debit_account_id',
            'default_credit_account_id',
            'payment_debit_account_id',
            'payment_credit_account_id',
            'suspense_account_id',
        ])
        self._cr.execute('''
            SELECT account.id, journal.id
            FROM account_account account
            JOIN res_company company ON company.id = account.company_id
            JOIN account_journal journal ON
                journal.default_debit_account_id = account.id
                OR
                journal.default_credit_account_id = account.id
            WHERE account.id IN %s
            AND journal.type IN ('bank', 'cash')
            AND journal.currency_id IS NOT NULL
            AND journal.currency_id != company.currency_id
            AND account.currency_id != journal.currency_id 
        ''', [tuple(self.ids)])
        res = self._cr.fetchone()
        if res:
            account = self.env['account.account'].browse(res[0])
            journal = self.env['account.journal'].browse(res[1])
            raise ValidationError(_("The foreign currency set on the journal '%s' and the account '%s' must be the same.") % (journal.display_name, account.display_name))

    @api.constrains('company_id')
    def _check_company_consistency(self):
        if not self:
            return

        self.flush(['company_id'])
        self._cr.execute('''
            SELECT line.id
            FROM account_move_line line
            JOIN account_account account ON account.id = line.account_id
            WHERE line.account_id IN %s
            AND line.company_id != account.company_id
        ''', [tuple(self.ids)])
        if self._cr.fetchone():
            raise UserError(_("You can't change the company of your account since there are some journal items linked to it."))

    @api.constrains('user_type_id')
    def _check_user_type_id(self):
        if not self:
            return

        self.flush(['user_type_id'])
        self._cr.execute('''
            SELECT account.id
            FROM account_account account
            JOIN account_account_type acc_type ON account.user_type_id = acc_type.id
            JOIN account_journal journal ON journal.default_credit_account_id = account.id OR journal.default_debit_account_id = account.id
            WHERE account.id IN %s
            AND acc_type.type IN ('receivable', 'payable')
            AND journal.type IN ('sale', 'purchase')
            LIMIT 1;
        ''', [tuple(self.ids)])

        if self._cr.fetchone():
            raise ValidationError(_("The account is already in use in a 'sale' or 'purchase' journal. This means that the account's type couldn't be 'receivable' or 'payable'."))

    @api.depends('code')
    def _compute_account_root(self):
        # this computes the first 2 digits of the account.
        # This field should have been a char, but the aim is to use it in a side panel view with hierarchy, and it's only supported by many2one fields so far.
        # So instead, we make it a many2one to a psql view with what we need as records.
        for record in self:
            record.root_id = (ord(record.code[0]) * 1000 + ord(record.code[1:2] or '\x00')) if record.code else False

    @api.depends('code')
    def _compute_account_group(self):
        if self.ids:
            self.env['account.group']._adapt_accounts_for_account_groups(self)
        else:
            self.group_id = False

    def _search_used(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        if operator != '=':
            value = not value
        self._cr.execute("""
            SELECT id FROM account_account account
            WHERE EXISTS (SELECT * FROM account_move_line aml WHERE aml.account_id = account.id LIMIT 1)
        """)
        return [('id', 'in' if value else 'not in', [r[0] for r in self._cr.fetchall()])]

    @api.model
    def _search_new_account_code(self, company, digits, prefix):
        for num in range(1, 10000):
            new_code = str(prefix.ljust(digits - 1, '0')) + str(num)
            rec = self.search([('code', '=', new_code), ('company_id', '=', company.id)], limit=1)
            if not rec:
                return new_code
        raise UserError(_('Cannot generate an unused account code.'))

    def _compute_opening_debit_credit(self):
        for record in self:
            opening_debit = opening_credit = 0.0
            if record.company_id.account_opening_move_id:
                for line in self.env['account.move.line'].search([('account_id', '=', record.id),
                                                                 ('move_id','=', record.company_id.account_opening_move_id.id)]):
                    if line.debit:
                        opening_debit += line.debit
                    elif line.credit:
                        opening_credit += line.credit
            record.opening_debit = opening_debit
            record.opening_credit = opening_credit

    def _set_opening_debit(self):
        self._set_opening_debit_credit(self.opening_debit, 'debit')

    def _set_opening_credit(self):
        self._set_opening_debit_credit(self.opening_credit, 'credit')

    def _set_opening_debit_credit(self, amount, field):
        """ Generic function called by both opening_debit and opening_credit's
        inverse function. 'Amount' parameter is the value to be set, and field
        either 'debit' or 'credit', depending on which one of these two fields
        got assigned.
        """
        opening_move = self.company_id.account_opening_move_id

        if not opening_move:
            raise UserError(_("You must first define an opening move."))

        if opening_move.state == 'draft':
            # check whether we should create a new move line or modify an existing one
            account_op_lines = self.env['account.move.line'].search([('account_id', '=', self.id),
                                                                      ('move_id','=', opening_move.id),
                                                                      (field,'!=', False),
                                                                      (field,'!=', 0.0)]) # 0.0 condition important for import

            if account_op_lines:
                op_aml_debit = sum(account_op_lines.mapped('debit'))
                op_aml_credit = sum(account_op_lines.mapped('credit'))

                # There might be more than one line on this account if the opening entry was manually edited
                # If so, we need to merge all those lines into one before modifying its balance
                opening_move_line = account_op_lines[0]
                if len(account_op_lines) > 1:
                    merge_write_cmd = [(1, opening_move_line.id, {'debit': op_aml_debit, 'credit': op_aml_credit, 'partner_id': None ,'name': _("Opening balance")})]
                    unlink_write_cmd = [(2, line.id) for line in account_op_lines[1:]]
                    opening_move.write({'line_ids': merge_write_cmd + unlink_write_cmd})

                if amount:
                    # modify the line
                    opening_move_line.with_context(check_move_validity=False)[field] = amount
                else:
                    # delete the line (no need to keep a line with value = 0)
                    opening_move_line.with_context(check_move_validity=False).unlink()

            elif amount:
                # create a new line, as none existed before
                self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'name': _('Opening balance'),
                        field: amount,
                        'move_id': opening_move.id,
                        'account_id': self.id,
                })

            # Then, we automatically balance the opening move, to make sure it stays valid
            if not 'import_file' in self.env.context:
                # When importing a file, avoid recomputing the opening move for each account and do it at the end, for better performances
                self.company_id._auto_balance_opening_move()

    @api.model
    def default_get(self, default_fields):
        """If we're creating a new account through a many2one, there are chances that we typed the account code
        instead of its name. In that case, switch both fields values.
        """
        default_name = self._context.get('default_name')
        default_code = self._context.get('default_code')
        if default_name and not default_code:
            try:
                default_code = int(default_name)
            except ValueError:
                pass
            if default_code:
                default_name = False
        contextual_self = self.with_context(default_name=default_name, default_code=default_code)
        return super(AccountAccount, contextual_self).default_get(default_fields)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        account_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(account_ids).with_user(name_get_uid))

    @api.onchange('user_type_id')
    def _onchange_user_type_id(self):
        self.reconcile = self.internal_type in ('receivable', 'payable')
        if self.internal_type == 'liquidity':
            self.reconcile = False
        elif self.internal_group == 'off_balance':
            self.reconcile = False
            self.tax_ids = False
        elif self.internal_group == 'income' and not self.tax_ids:
            self.tax_ids = self.company_id.account_sale_tax_id
        elif self.internal_group == 'expense' and not self.tax_ids:
            self.tax_ids = self.company_id.account_purchase_tax_id

    def name_get(self):
        result = []
        for account in self:
            name = account.code + ' ' + account.name
            result.append((account.id, name))
        return result

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if default.get('code', False):
            return super(AccountAccount, self).copy(default)
        try:
            default['code'] = (str(int(self.code) + 10) or '').zfill(len(self.code))
            default.setdefault('name', _("%s (copy)") % (self.name or ''))
            while self.env['account.account'].search([('code', '=', default['code']),
                                                      ('company_id', '=', default.get('company_id', False) or self.company_id.id)], limit=1):
                default['code'] = (str(int(default['code']) + 10) or '')
                default['name'] = _("%s (copy)") % (self.name or '')
        except ValueError:
            default['code'] = _("%s (copy)") % (self.code or '')
            default['name'] = self.name
        return super(AccountAccount, self).copy(default)

    @api.model
    def load(self, fields, data):
        """ Overridden for better performances when importing a list of account
        with opening debit/credit. In that case, the auto-balance is postpone
        until the whole file has been imported.
        """
        rslt = super(AccountAccount, self).load(fields, data)

        if 'import_file' in self.env.context:
            companies = self.search([('id', 'in', rslt['ids'])]).mapped('company_id')
            for company in companies:
                company._auto_balance_opening_move()
        return rslt

    def _toggle_reconcile_to_true(self):
        '''Toggle the `reconcile´ boolean from False -> True

        Note that: lines with debit = credit = amount_currency = 0 are set to `reconciled´ = True
        '''
        if not self.ids:
            return None
        query = """
            UPDATE account_move_line SET
                reconciled = CASE WHEN debit = 0 AND credit = 0 AND amount_currency = 0
                    THEN true ELSE false END,
                amount_residual = (debit-credit),
                amount_residual_currency = amount_currency
            WHERE full_reconcile_id IS NULL and account_id IN %s
        """
        self.env.cr.execute(query, [tuple(self.ids)])

    def _toggle_reconcile_to_false(self):
        '''Toggle the `reconcile´ boolean from True -> False

        Note that it is disallowed if some lines are partially reconciled.
        '''
        if not self.ids:
            return None
        partial_lines_count = self.env['account.move.line'].search_count([
            ('account_id', 'in', self.ids),
            ('full_reconcile_id', '=', False),
            ('|'),
            ('matched_debit_ids', '!=', False),
            ('matched_credit_ids', '!=', False),
        ])
        if partial_lines_count > 0:
            raise UserError(_('You cannot switch an account to prevent the reconciliation '
                              'if some partial reconciliations are still pending.'))
        query = """
            UPDATE account_move_line
                SET amount_residual = 0, amount_residual_currency = 0
            WHERE full_reconcile_id = NULL AND account_id IN %s
        """
        self.env.cr.execute(query, [tuple(self.ids)])

    def write(self, vals):
        # Do not allow changing the company_id when account_move_line already exist
        if vals.get('company_id', False):
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            for account in self:
                if (account.company_id.id != vals['company_id']) and move_lines:
                    raise UserError(_('You cannot change the owner company of an account that already contains journal items.'))
        if 'reconcile' in vals:
            if vals['reconcile']:
                self.filtered(lambda r: not r.reconcile)._toggle_reconcile_to_true()
            else:
                self.filtered(lambda r: r.reconcile)._toggle_reconcile_to_false()

        if vals.get('currency_id'):
            for account in self:
                if self.env['account.move.line'].search_count([('account_id', '=', account.id), ('currency_id', 'not in', (False, vals['currency_id']))]):
                    raise UserError(_('You cannot set a currency on this account as it already has some journal entries having a different foreign currency.'))

        return super(AccountAccount, self).write(vals)

    def unlink(self):
        if self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot perform this action on an account that contains journal items.'))
        #Checking whether the account is set as a property to any Partner or not
        values = ['account.account,%s' % (account_id,) for account_id in self.ids]
        partner_prop_acc = self.env['ir.property'].search([('value_reference', 'in', values)], limit=1)
        if partner_prop_acc:
            raise UserError(_('You cannot remove/deactivate an account which is set on a customer or vendor.'))
        return super(AccountAccount, self).unlink()

    def action_read_account(self):
        self.ensure_one()
        return {
            'name': self.display_name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.account',
            'res_id': self.id,
        }

    def action_duplicate_accounts(self):
        for account in self.browse(self.env.context['active_ids']):
            account.copy()


class AccountGroup(models.Model):
    _name = "account.group"
    _description = 'Account Group'
    _parent_store = True
    _order = 'code_prefix_start'

    parent_id = fields.Many2one('account.group', index=True, ondelete='cascade', readonly=True)
    parent_path = fields.Char(index=True)
    name = fields.Char(required=True)
    code_prefix_start = fields.Char()
    code_prefix_end = fields.Char()
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

    _sql_constraints = [
        (
            'check_length_prefix',
            'CHECK(char_length(COALESCE(code_prefix_start, \'\')) = char_length(COALESCE(code_prefix_end, \'\')))',
            'The length of the starting and the ending code prefix must be the same'
        ),
    ]

    @api.onchange('code_prefix_start')
    def _onchange_code_prefix_start(self):
        if not self.code_prefix_end or self.code_prefix_end < self.code_prefix_start:
            self.code_prefix_end = self.code_prefix_start

    @api.onchange('code_prefix_end')
    def _onchange_code_prefix_end(self):
        if not self.code_prefix_start or self.code_prefix_start > self.code_prefix_end:
            self.code_prefix_start = self.code_prefix_end

    def name_get(self):
        result = []
        for group in self:
            prefix = group.code_prefix_start and str(group.code_prefix_start)
            if prefix and group.code_prefix_end != group.code_prefix_start:
                prefix += '-' + str(group.code_prefix_end)
            name = (prefix and (prefix + ' ') or '') + group.name
            result.append((group.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            criteria_operator = ['|'] if operator not in expression.NEGATIVE_TERM_OPERATORS else ['&', '!']
            domain = criteria_operator + [('code_prefix_start', '=ilike', name + '%'), ('name', operator, name)]
        group_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(group_ids).with_user(name_get_uid))

    @api.constrains('code_prefix_start', 'code_prefix_end')
    def _constraint_prefix_overlap(self):
        self.env['account.group'].flush()
        query = """
            SELECT other.id FROM account_group this
            JOIN account_group other
              ON char_length(other.code_prefix_start) = char_length(this.code_prefix_start)
             AND other.id != this.id
             AND other.company_id = this.company_id
             AND (
                other.code_prefix_start <= this.code_prefix_start AND this.code_prefix_start <= other.code_prefix_end
                OR
                other.code_prefix_start >= this.code_prefix_start AND this.code_prefix_end >= other.code_prefix_start
            )
            WHERE this.id IN %(ids)s
        """
        self.env.cr.execute(query, {'ids': tuple(self.ids)})
        res = self.env.cr.fetchall()
        if res:
            raise ValidationError(_('Account Groups with the same granularity can\'t overlap'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'code_prefix_start' in vals and not vals.get('code_prefix_end'):
                vals['code_prefix_end'] = vals['code_prefix_start']
        res_ids = super(AccountGroup, self).create(vals_list)
        res_ids._adapt_accounts_for_account_groups()
        res_ids._adapt_parent_account_group()
        return res_ids

    def write(self, vals):
        res = super(AccountGroup, self).write(vals)
        if 'code_prefix_start' in vals or 'code_prefix_end' in vals:
            self._adapt_accounts_for_account_groups()
            self._adapt_parent_account_group()
        return res

    def unlink(self):
        for record in self:
            account_ids = self.env['account.account'].search([('group_id', '=', record.id)])
            account_ids.write({'group_id': record.parent_id.id})

            children_ids = self.env['account.group'].search([('parent_id', '=', record.id)])
            children_ids.write({'parent_id': record.parent_id.id})
        super(AccountGroup, self).unlink()

    def _adapt_accounts_for_account_groups(self, account_ids=None):
        """Ensure consistency between accounts and account groups.

        Find and set the most specific group matching the code of the account.
        The most specific is the one with the longest prefixes and with the starting
        prefix being smaller than the account code and the ending prefix being greater.
        """
        if not self and not account_ids:
            return
        self.env['account.group'].flush()
        self.env['account.account'].flush()
        query = """
            UPDATE account_account account SET group_id = (
                SELECT agroup.id FROM account_group agroup
                WHERE agroup.code_prefix_start <= LEFT(account.code, char_length(agroup.code_prefix_start))
                AND agroup.code_prefix_end >= LEFT(account.code, char_length(agroup.code_prefix_end))
                AND agroup.company_id = account.company_id
                ORDER BY char_length(agroup.code_prefix_start) DESC LIMIT 1
            ) WHERE account.company_id in %(company_ids)s {where_account};
        """.format(
            where_account=account_ids and 'AND account.id IN %(account_ids)s' or ''
        )
        self.env.cr.execute(query, {'company_ids': tuple((self.company_id or account_ids.company_id).ids), 'account_ids': account_ids and tuple(account_ids.ids)})
        self.env['account.account'].invalidate_cache(fnames=['group_id'])

    def _adapt_parent_account_group(self):
        """Ensure consistency of the hierarchy of account groups.

        Find and set the most specific parent for each group.
        The most specific is the one with the longest prefixes and with the starting
        prefix being smaller than the child prefixes and the ending prefix being greater.
        """
        if not self:
            return
        self.env['account.group'].flush()
        query = """
            UPDATE account_group agroup SET parent_id = (
                SELECT parent.id FROM account_group parent
                WHERE char_length(parent.code_prefix_start) < char_length(agroup.code_prefix_start)
                AND parent.code_prefix_start <= LEFT(agroup.code_prefix_start, char_length(parent.code_prefix_start))
                AND parent.code_prefix_end >= LEFT(agroup.code_prefix_end, char_length(parent.code_prefix_end))
                AND parent.id != agroup.id
                AND parent.company_id = %(company_id)s
                ORDER BY char_length(parent.code_prefix_start) DESC LIMIT 1
            ) WHERE agroup.company_id = %(company_id)s;
        """
        self.env.cr.execute(query, {'company_id': self.company_id.id})
        self.env['account.group'].invalidate_cache(fnames=['parent_id'])
        self.env['account.group'].search([('company_id', '=', self.company_id.id)])._parent_store_update()


class AccountRoot(models.Model):
    _name = 'account.root'
    _description = 'Account codes first 2 digits'
    _auto = False

    name = fields.Char()
    parent_id = fields.Many2one('account.root')
    company_id = fields.Many2one('res.company')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
            CREATE OR REPLACE VIEW %s AS (
            SELECT DISTINCT ASCII(code) * 1000 + ASCII(SUBSTRING(code,2,1)) AS id,
                   LEFT(code,2) AS name,
                   ASCII(code) AS parent_id,
                   company_id
            FROM account_account WHERE code IS NOT NULL
            UNION ALL
            SELECT DISTINCT ASCII(code) AS id,
                   LEFT(code,1) AS name,
                   NULL::int AS parent_id,
                   company_id
            FROM account_account WHERE code IS NOT NULL
            )''' % (self._table,)
        )


class AccountJournalGroup(models.Model):
    _name = 'account.journal.group'
    _description = "Account Journal Group"
    _check_company_auto = True

    name = fields.Char("Journal Group", required=True, translate=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    excluded_journal_ids = fields.Many2many('account.journal', string="Excluded Journals", domain="[('company_id', '=', company_id)]",
        check_company=True)
    sequence = fields.Integer(default=10)


class AccountJournal(models.Model):
    _name = "account.journal"
    _description = "Journal"
    _order = 'sequence, type, code'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    def _default_inbound_payment_methods(self):
        return self.env.ref('account.account_payment_method_manual_in')

    def _default_outbound_payment_methods(self):
        return self.env.ref('account.account_payment_method_manual_out')

    def __get_bank_statements_available_sources(self):
        return [('undefined', _('Undefined Yet'))]

    def _get_bank_statements_available_sources(self):
        return self.__get_bank_statements_available_sources()

    name = fields.Char(string='Journal Name', required=True)
    code = fields.Char(string='Short Code', size=5, required=True, help="Shorter name used for display. The journal entries of this journal will also be named using this prefix by default.")
    active = fields.Boolean(default=True, help="Set active to false to hide the Journal without removing it.")
    type = fields.Selection([
            ('sale', 'Sales'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('general', 'Miscellaneous'),
        ], required=True,
        help="Select 'Sale' for customer invoices journals.\n"\
        "Select 'Purchase' for vendor bills journals.\n"\
        "Select 'Cash' or 'Bank' for journals that are used in customer or vendor payments.\n"\
        "Select 'General' for miscellaneous operations journals.")
    type_control_ids = fields.Many2many('account.account.type', 'journal_account_type_control_rel', 'journal_id', 'type_id', string='Account Types Allowed')
    account_control_ids = fields.Many2many('account.account', 'journal_account_control_rel', 'journal_id', 'account_id', string='Accounts Allowed',
        check_company=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    default_credit_account_id = fields.Many2one('account.account', string='Default Credit Account', copy=False,
        domain=[('deprecated', '=', False)], help="It acts as a default account for credit amount",
        check_company=True,
        ondelete='restrict')
    default_debit_account_id = fields.Many2one('account.account', string='Default Debit Account', copy=False,
        check_company=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", help="It acts as a default account for debit amount", ondelete='restrict')
    payment_debit_account_id = fields.Many2one('account.account', string='Outstanding Receipts Account', copy=False,
        ondelete='restrict',
        domain=[('deprecated', '=', False)],
        help="Incoming payments entries triggered by invoices/refunds will be posted on the Outstanding Receipts Account "
             "and displayed as blue lines in the bank reconciliation widget. During the reconciliation process, concerned "
             "transactions will be reconciled with entries on the Outstanding Receipts Account instead of the "
             "receivable account.")
    payment_credit_account_id = fields.Many2one('account.account', string='Outstanding Payments Account', copy=False,
        ondelete='restrict',
        domain=[('deprecated', '=', False)],
        help="Outgoing payments entries triggered by bills/credit notes will be posted on the Outstanding Payments Account "
             "and displayed as blue lines in the bank reconciliation widget. During the reconciliation process, concerned "
             "transactions will be reconciled with entries on the Outstanding Payments Account instead of the "
             "payable account.")
    suspense_account_id = fields.Many2one('account.account', string='Bank Suspense Account',
        ondelete='restrict', readonly=False, store=True, require=True,
        compute='_compute_suspense_account_id',
        domain=[('deprecated', '=', False), ('reconcile', '=', True)],
        help="Bank statements transactions will be posted on the suspense account until the final reconciliation "
             "allowing finding the right account.")
    restrict_mode_hash_table = fields.Boolean(string="Lock Posted Entries with Hash",
        help="If ticked, the accounting entry or invoice receives a hash as soon as it is posted and cannot be modified anymore.")
    sequence = fields.Integer(help='Used to order Journals in the dashboard view', default=10)

    invoice_reference_type = fields.Selection(string='Communication Type', required=True, selection=[('none', 'Free'), ('partner', 'Based on Customer'), ('invoice', 'Based on Invoice')], default='invoice', help='You can set here the default communication that will appear on customer invoices, once validated, to help the customer to refer to that particular invoice when making the payment.')
    invoice_reference_model = fields.Selection(string='Communication Standard', required=True, selection=[('odoo', 'Odoo'),('euro', 'European')], default='odoo', help="You can choose different models for each type of reference. The default one is the Odoo reference.")

    #groups_id = fields.Many2many('res.groups', 'account_journal_group_rel', 'journal_id', 'group_id', string='Groups')
    currency_id = fields.Many2one('res.currency', help='The currency used to enter statement', string="Currency")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, index=True, default=lambda self: self.env.company,
        help="Company related to this journal")

    refund_sequence = fields.Boolean(string='Dedicated Credit Note Sequence', help="Check this box if you don't want to share the same sequence for invoices and credit notes made from this journal", default=False)
    sequence_override_regex = fields.Text(help="Technical field used to enforce complex sequence composition that the system would normally misunderstand.\n"\
                                          "This is a regex that can include all the following capture groups: prefix1, year, prefix2, month, prefix3, seq, suffix.\n"\
                                          "The prefix* groups are the separators between the year, month and the actual increasing sequence number (seq).\n"\
                                          
                                          "e.g: ^(?P<prefix1>.*?)(?P<year>\d{4})(?P<prefix2>\D*?)(?P<month>\d{2})(?P<prefix3>\D+?)(?P<seq>\d+)(?P<suffix>\D*?)$")

    inbound_payment_method_ids = fields.Many2many('account.payment.method', 'account_journal_inbound_payment_method_rel', 'journal_id', 'inbound_payment_method',
        domain=[('payment_type', '=', 'inbound')], string='For Incoming Payments', default=lambda self: self._default_inbound_payment_methods(),
        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n"\
             "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n"\
             "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo,you are suggested to reconcile the transaction with the batch deposit. Enable this option from the settings.")
    outbound_payment_method_ids = fields.Many2many('account.payment.method', 'account_journal_outbound_payment_method_rel', 'journal_id', 'outbound_payment_method',
        domain=[('payment_type', '=', 'outbound')], string='For Outgoing Payments', default=lambda self: self._default_outbound_payment_methods(),
        help="Manual:Pay bill by cash or any other method outside of Odoo.\n"\
             "Check:Pay bill by check and print it from Odoo.\n"\
             "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. Enable this option from the settings.")
    at_least_one_inbound = fields.Boolean(compute='_methods_compute', store=True)
    at_least_one_outbound = fields.Boolean(compute='_methods_compute', store=True)
    profit_account_id = fields.Many2one('account.account',
        string='Profit Account',
        domain="[('company_id', '=', company_id)]",
        check_company=True,
        help="Used to register a profit when the ending balance of a cash register differs from what the system computes")
    loss_account_id = fields.Many2one('account.account',
        string='Loss Account',
        domain="[('company_id', '=', company_id)]",
        check_company=True,
        help="Used to register a loss when the ending balance of a cash register differs from what the system computes")

    # Bank journals fields
    company_partner_id = fields.Many2one('res.partner', related='company_id.partner_id', string='Account Holder', readonly=True, store=False)
    bank_account_id = fields.Many2one('res.partner.bank',
        string="Bank Account",
        ondelete='restrict', copy=False,
        check_company=True,
        domain="[('partner_id','=', company_partner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    bank_statements_source = fields.Selection(selection=_get_bank_statements_available_sources, string='Bank Feeds', default='undefined', help="Defines how the bank statements will be registered")
    bank_acc_number = fields.Char(related='bank_account_id.acc_number', readonly=False)
    bank_id = fields.Many2one('res.bank', related='bank_account_id.bank_id', readonly=False)

    # Sale journals fields
    sale_activity_type_id = fields.Many2one('mail.activity.type', string='Schedule Activity', default=False, help="Activity will be automatically scheduled on payment due date, improving collection process.")
    sale_activity_user_id = fields.Many2one('res.users', string="Activity User", help="Leave empty to assign the Salesperson of the invoice.")
    sale_activity_note = fields.Text('Activity Summary')

    # alias configuration for journals
    alias_id = fields.Many2one('mail.alias', string='Alias', copy=False)
    alias_domain = fields.Char('Alias domain', compute='_compute_alias_domain', default=lambda self: self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain"))
    alias_name = fields.Char('Alias Name', related='alias_id.alias_name', help="It creates draft invoices and bills by sending an email.", readonly=False)

    journal_group_ids = fields.Many2many('account.journal.group',
        domain="[('company_id', '=', company_id)]",
        check_company=True,
        string="Journal Groups")

    secure_sequence_id = fields.Many2one('ir.sequence',
        help='Sequence to use to ensure the securisation of data',
        check_company=True,
        readonly=True, copy=False)

    _sql_constraints = [
        ('code_company_uniq', 'unique (code, name, company_id)', 'The code and name of the journal must be unique per company !'),
    ]

    @api.depends('company_id', 'type')
    def _compute_suspense_account_id(self):
        for journal in self:
            if journal.type not in ('bank', 'cash'):
                journal.suspense_account_id = False
            elif journal.suspense_account_id:
                journal.suspense_account_id = journal.suspense_account_id
            elif journal.company_id.account_journal_suspense_account_id:
                journal.suspense_account_id = journal.company_id.account_journal_suspense_account_id
            else:
                journal.suspense_account_id = False

    def _compute_alias_domain(self):
        alias_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
        for record in self:
            record.alias_domain = alias_domain

    @api.constrains('type_control_ids')
    def _constrains_type_control_ids(self):
        self.env['account.move.line'].flush(['account_id', 'journal_id'])
        self.flush(['type_control_ids'])
        self._cr.execute("""
            SELECT aml.id
            FROM account_move_line aml
            WHERE aml.journal_id in (%s)
            AND EXISTS (SELECT 1 FROM journal_account_type_control_rel rel WHERE rel.journal_id = aml.journal_id)
            AND NOT EXISTS (SELECT 1 FROM account_account acc
                            JOIN journal_account_type_control_rel rel ON acc.user_type_id = rel.type_id
                            WHERE acc.id = aml.account_id AND rel.journal_id = aml.journal_id)
        """, tuple(self.ids))
        if self._cr.fetchone():
            raise ValidationError(_('Some journal items already exist in this journal but with accounts from different types than the allowed ones.'))

    @api.constrains('account_control_ids')
    def _constrains_account_control_ids(self):
        self.env['account.move.line'].flush(['account_id', 'journal_id'])
        self.flush(['account_control_ids'])
        self._cr.execute("""
            SELECT aml.id
            FROM account_move_line aml
            WHERE aml.journal_id in (%s)
            AND EXISTS (SELECT 1 FROM journal_account_control_rel rel WHERE rel.journal_id = aml.journal_id)
            AND NOT EXISTS (SELECT 1 FROM journal_account_control_rel rel WHERE rel.account_id = aml.account_id AND rel.journal_id = aml.journal_id)
        """, tuple(self.ids))
        if self._cr.fetchone():
            raise ValidationError(_('Some journal items already exist in this journal but with other accounts than the allowed ones.'))

    @api.constrains('type', 'bank_account_id')
    def _check_bank_account(self):
        for journal in self:
            if journal.type == 'bank' and journal.bank_account_id:
                if journal.bank_account_id.company_id and journal.bank_account_id.company_id != journal.company_id:
                    raise ValidationError(_('The bank account of a bank journal must belong to the same company (%s).') % journal.company_id.name)
                # A bank account can belong to a customer/supplier, in which case their partner_id is the customer/supplier.
                # Or they are part of a bank journal and their partner_id must be the company's partner_id.
                if journal.bank_account_id.partner_id != journal.company_id.partner_id:
                    raise ValidationError(_('The holder of a journal\'s bank account must be the company (%s).') % journal.company_id.name)

    @api.constrains('company_id')
    def _check_company_consistency(self):
        if not self:
            return

        self.flush(['company_id'])
        self._cr.execute('''
            SELECT move.id
            FROM account_move move
            JOIN account_journal journal ON journal.id = move.journal_id
            WHERE move.journal_id IN %s
            AND move.company_id != journal.company_id
        ''', [tuple(self.ids)])
        if self._cr.fetchone():
            raise UserError(_("You can't change the company of your journal since there are some journal entries linked to it."))

    @api.constrains('default_debit_account_id', 'default_credit_account_id', 'payment_debit_account_id', 'payment_credit_account_id')
    def _check_journal_not_shared_accounts(self):
        accounts = self.default_debit_account_id \
                   + self.default_credit_account_id \
                   + self.payment_debit_account_id \
                   + self.payment_credit_account_id

        if not accounts:
            return

        self.env['account.journal'].flush([
            'default_debit_account_id',
            'default_credit_account_id',
            'payment_debit_account_id',
            'payment_credit_account_id',
        ])
        self._cr.execute('''
            SELECT
                account.name,
                ARRAY_AGG(DISTINCT journal.name) AS journal_names
            FROM account_account account
            LEFT JOIN account_journal journal ON
                journal.default_debit_account_id = account.id
                OR
                journal.default_credit_account_id = account.id
                OR
                journal.payment_debit_account_id = account.id
                OR
                journal.payment_credit_account_id = account.id
            WHERE account.id IN %s
            GROUP BY account.name
            HAVING COUNT(DISTINCT journal.id) > 1
        ''', [tuple(accounts.ids)])
        res = self._cr.fetchone()
        if res:
            raise ValidationError(_("The account %s can't be shared between multiple journals: %s") % (res[0], ', '.join(res[1])))

    @api.constrains('type', 'default_credit_account_id', 'default_debit_account_id')
    def _check_type_default_credit_account_id_type(self):
        journals_to_check = self.filtered(lambda journal: journal.type in ('sale', 'purchase'))
        accounts_to_check = journals_to_check.mapped('default_debit_account_id') + journals_to_check.mapped('default_credit_account_id')
        if any(account.user_type_id.type in ('receivable', 'payable') for account in accounts_to_check):
            raise ValidationError(_("The type of the journal's default credit/debit account shouldn't be 'receivable' or 'payable'."))

    @api.onchange('default_debit_account_id')
    def onchange_debit_account_id(self):
        if not self.default_credit_account_id:
            self.default_credit_account_id = self.default_debit_account_id

    @api.onchange('default_credit_account_id')
    def onchange_credit_account_id(self):
        if not self.default_debit_account_id:
            self.default_debit_account_id = self.default_credit_account_id

    @api.onchange('type')
    def _onchange_type(self):
        self.refund_sequence = self.type in ('sale', 'purchase')

    def _get_alias_values(self, type, alias_name=None):
        if not alias_name:
            alias_name = self.name
            if self.company_id != self.env.ref('base.main_company'):
                alias_name += '-' + str(self.company_id.name)
        return {
            'alias_defaults': {'move_type': type == 'purchase' and 'in_invoice' or 'out_invoice', 'company_id': self.company_id.id, 'journal_id': self.id},
            'alias_parent_thread_id': self.id,
            'alias_name': alias_name,
        }

    def unlink(self):
        bank_accounts = self.env['res.partner.bank'].browse()
        for bank_account in self.mapped('bank_account_id'):
            accounts = self.search([('bank_account_id', '=', bank_account.id)])
            if accounts <= self:
                bank_accounts += bank_account
        self.mapped('alias_id').unlink()
        ret = super(AccountJournal, self).unlink()
        bank_accounts.unlink()
        return ret

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            code=_("%s (copy)") % (self.code or ''),
            name=_("%s (copy)") % (self.name or ''))
        return super(AccountJournal, self).copy(default)

    def _update_mail_alias(self, vals):
        self.ensure_one()
        alias_values = self._get_alias_values(type=vals.get('type') or self.type, alias_name=vals.get('alias_name'))
        if self.alias_id:
            self.alias_id.write(alias_values)
        else:
            self.alias_id = self.env['mail.alias'].with_context(alias_model_name='account.move',
                alias_parent_model_name='account.journal').create(alias_values)

        if vals.get('alias_name'):
            # remove alias_name to avoid useless write on alias
            del(vals['alias_name'])

    def write(self, vals):
        for journal in self:
            company = journal.company_id
            if ('company_id' in vals and journal.company_id.id != vals['company_id']):
                if self.env['account.move'].search([('journal_id', '=', journal.id)], limit=1):
                    raise UserError(_('This journal already contains items, therefore you cannot modify its company.'))
                company = self.env['res.company'].browse(vals['company_id'])
                if journal.bank_account_id.company_id and journal.bank_account_id.company_id != company:
                    journal.bank_account_id.write({
                        'company_id': company.id,
                        'partner_id': company.partner_id.id,
                    })
            if 'currency_id' in vals:
                if journal.bank_account_id:
                    journal.bank_account_id.currency_id = vals['currency_id']
            if 'bank_account_id' in vals:
                if not vals.get('bank_account_id'):
                    raise UserError(_('You cannot remove the bank account from the journal once set.'))
                else:
                    bank_account = self.env['res.partner.bank'].browse(vals['bank_account_id'])
                    if bank_account.partner_id != company.partner_id:
                        raise UserError(_("The partners of the journal's company and the related bank account mismatch."))
            if 'alias_name' in vals:
                journal._update_mail_alias(vals)
            if 'restrict_mode_hash_table' in vals and not vals.get('restrict_mode_hash_table'):
                journal_entry = self.env['account.move'].search([('journal_id', '=', self.id), ('state', '=', 'posted'), ('secure_sequence_number', '!=', 0)], limit=1)
                if len(journal_entry) > 0:
                    field_string = self._fields['restrict_mode_hash_table'].get_description(self.env)['string']
                    raise UserError(_("You cannot modify the field %s of a journal that already has accounting entries.") % field_string)
        result = super(AccountJournal, self).write(vals)

        for journal in self:
            # Ensure the liquidity accounts are sharing the same foreign currency.
            accounts = journal.default_debit_account_id + journal.default_credit_account_id
            accounts.write({'currency_id': journal.currency_id.id})

        # Create the bank_account_id if necessary
        if 'bank_acc_number' in vals:
            for journal in self.filtered(lambda r: r.type == 'bank' and not r.bank_account_id):
                journal.set_bank_account(vals.get('bank_acc_number'), vals.get('bank_id'))
        for record in self:
            if record.restrict_mode_hash_table and not record.secure_sequence_id:
                record._create_secure_sequence(['secure_sequence_id'])

        return result

    @api.model
    def get_next_bank_cash_default_code(self, journal_type, company):
        journal_code_base = (journal_type == 'cash' and 'CSH' or 'BNK')
        journals = self.env['account.journal'].search([('code', 'like', journal_code_base + '%'), ('company_id', '=', company.id)])
        for num in range(1, 100):
            # journal_code has a maximal size of 5, hence we can enforce the boundary num < 100
            journal_code = journal_code_base + str(num)
            if journal_code not in journals.mapped('code'):
                return journal_code

    @api.model
    def _fill_missing_values(self, vals):
        journal_type = vals.get('type')

        # 'type' field is required.
        if not journal_type:
            return

        # === Fill missing company ===
        company = self.env['res.company'].browse(vals['company_id']) if vals.get('company_id') else self.env.company
        vals['company_id'] = company.id

        # Don't get the digits on 'chart_template_id' since the chart template could be a custom one.
        random_account = self.env['account.account'].search([('company_id', '=', company.id)], limit=1)
        digits = len(random_account.code) if random_account else 6

        liquidity_type = self.env.ref('account.data_account_type_liquidity')
        current_assets_type = self.env.ref('account.data_account_type_current_assets')

        if journal_type in ('bank', 'cash'):
            has_liquidity_accounts = vals.get('default_debit_account_id') or vals.get('default_credit_account_id')
            has_payment_accounts = vals.get('payment_debit_account_id') or vals.get('payment_credit_account_id')
            has_profit_account = vals.get('profit_account_id')
            has_loss_account = vals.get('loss_account_id')

            if journal_type == 'bank':
                liquidity_account_prefix = company.bank_account_code_prefix or ''
            else:
                liquidity_account_prefix = company.cash_account_code_prefix or company.bank_account_code_prefix or ''

            # === Fill missing name ===
            vals['name'] = vals.get('name') or vals.get('bank_acc_number')

            # === Fill missing code ===
            if 'code' not in vals:
                vals['code'] = self.get_next_bank_cash_default_code(journal_type, company)
                if not vals['code']:
                    raise UserError(_("Cannot generate an unused journal code. Please fill the 'Shortcode' field."))

            # === Fill missing accounts ===
            if not has_liquidity_accounts:
                liquidity_account = self.env['account.account'].create({
                    'name': vals.get('name'),
                    'code': self.env['account.account']._search_new_account_code(company, digits, liquidity_account_prefix),
                    'user_type_id': liquidity_type.id,
                    'currency_id': vals.get('currency_id'),
                    'company_id': company.id,
                })

                vals.update({
                    'default_debit_account_id': liquidity_account.id,
                    'default_credit_account_id': liquidity_account.id,
                })
            if not has_payment_accounts:
                vals['payment_debit_account_id'] = self.env['account.account'].create({
                    'name': _("Outstanding Receipts"),
                    'code': self.env['account.account']._search_new_account_code(company, digits, liquidity_account_prefix),
                    'reconcile': True,
                    'user_type_id': current_assets_type.id,
                    'company_id': company.id,
                }).id
                vals['payment_credit_account_id'] = self.env['account.account'].create({
                    'name': _("Outstanding Payments"),
                    'code': self.env['account.account']._search_new_account_code(company, digits, liquidity_account_prefix),
                    'reconcile': True,
                    'user_type_id': current_assets_type.id,
                    'company_id': company.id,
                }).id
            if journal_type == 'cash' and not has_profit_account:
                vals['profit_account_id'] = company.default_cash_difference_income_account_id.id
            if journal_type == 'cash' and not has_loss_account:
                vals['loss_account_id'] = company.default_cash_difference_expense_account_id.id

        # === Fill missing refund_sequence ===
        if 'refund_sequence' not in vals:
            vals['refund_sequence'] = vals['type'] in ('sale', 'purchase')

    @api.model
    def create(self, vals):
        # OVERRIDE
        self._fill_missing_values(vals)

        journal = super(AccountJournal, self.with_context(mail_create_nolog=True)).create(vals)

        if 'alias_name' in vals:
            journal._update_mail_alias(vals)

        # Create the bank_account_id if necessary
        if journal.type == 'bank' and not journal.bank_account_id and vals.get('bank_acc_number'):
            journal.set_bank_account(vals.get('bank_acc_number'), vals.get('bank_id'))

        return journal

    def set_bank_account(self, acc_number, bank_id=None):
        """ Create a res.partner.bank and set it as value of the  field bank_account_id """
        self.ensure_one()
        self.bank_account_id = self.env['res.partner.bank'].create({
            'acc_number': acc_number,
            'bank_id': bank_id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.company_id.partner_id.id,
        }).id

    def name_get(self):
        res = []
        for journal in self:
            name = journal.name
            if journal.currency_id and journal.currency_id != journal.company_id.currency_id:
                name = "%s (%s)" % (name, journal.currency_id.name)
            res += [(journal.id, name)]
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []

        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            connector = '&' if operator in expression.NEGATIVE_TERM_OPERATORS else '|'
            domain = [connector, ('code', operator, name), ('name', operator, name)]
        journal_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(journal_ids).with_user(name_get_uid))

    @api.depends('inbound_payment_method_ids', 'outbound_payment_method_ids')
    def _methods_compute(self):
        for journal in self:
            journal.at_least_one_inbound = bool(len(journal.inbound_payment_method_ids))
            journal.at_least_one_outbound = bool(len(journal.outbound_payment_method_ids))

    def action_configure_bank_journal(self):
        """ This function is called by the "configure" button of bank journals,
        visible on dashboard if no bank statement source has been defined yet
        """
        # We simply call the setup bar function.
        return self.env['res.company'].setting_init_bank_account_action()

    def create_invoice_from_attachment(self, attachment_ids=[]):
        ''' Create the invoices from files.
         :return: A action redirecting to account.move tree/form view.
        '''
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        if not attachments:
            raise UserError(_("No attachment was provided"))

        invoices = self.env['account.move']
        for attachment in attachments:
            invoice = self.env['account.move'].create({})
            attachment.write({'res_model': 'mail.compose.message'})
            invoice.message_post(attachment_ids=[attachment.id])
            invoices += invoice

        action_vals = {
            'name': _('Generated Documents'),
            'domain': [('id', 'in', invoices.ids)],
            'res_model': 'account.move',
            'views': [[False, "tree"], [False, "form"]],
            'type': 'ir.actions.act_window',
            'context': self._context
        }
        if len(invoices) == 1:
            action_vals.update({'res_id': invoices[0].id, 'view_mode': 'form'})
        else:
            action_vals['view_mode'] = 'tree,form'
        return action_vals

    def _create_secure_sequence(self, sequence_fields):
        """This function creates a no_gap sequence on each journal in self that will ensure
        a unique number is given to all posted account.move in such a way that we can always
        find the previous move of a journal entry on a specific journal.
        """
        for journal in self:
            vals_write = {}
            for seq_field in sequence_fields:
                if not journal[seq_field]:
                    vals = {
                        'name': _('Securisation of %s - %s') % (seq_field, journal.name),
                        'code': 'SECUR%s-%s' % (journal.id, seq_field),
                        'implementation': 'no_gap',
                        'prefix': '',
                        'suffix': '',
                        'padding': 0,
                        'company_id': journal.company_id.id}
                    seq = self.env['ir.sequence'].create(vals)
                    vals_write[seq_field] = seq.id
            if vals_write:
                journal.write(vals_write)

    # -------------------------------------------------------------------------
    # REPORTING METHODS
    # -------------------------------------------------------------------------

    def _get_journal_bank_account_balance(self, domain=None):
        ''' Get the bank balance of the current journal by filtering the journal items using the journal's accounts.

        /!\ The current journal is not part of the applied domain. This is the expected behavior since we only want
        a logic based on accounts.

        :param domain:  An additional domain to be applied on the account.move.line model.
        :return:        The balance expressed in the journal's currency.
        '''
        self.ensure_one()
        self.env['account.move.line'].check_access_rights('read')

        accounts = self.default_debit_account_id + self.default_credit_account_id
        if not accounts:
            return 0.0

        domain = (domain or []) + [
            ('account_id', 'in', tuple(accounts.ids)),
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('move_id.state', '!=', 'cancel'),
        ]
        query = self.env['account.move.line']._where_calc(domain)
        tables, where_clause, where_params = query.get_sql()

        query = '''
            SELECT
                COUNT(account_move_line.id) AS nb_lines,
                COALESCE(SUM(account_move_line.balance), 0.0),
                COALESCE(SUM(account_move_line.amount_currency), 0.0)
            FROM ''' + tables + '''
            WHERE ''' + where_clause + '''
        '''
        self._cr.execute(query, where_params)

        company_currency = self.company_id.currency_id
        journal_currency = self.currency_id if self.currency_id and self.currency_id != company_currency else False

        nb_lines, balance, amount_currency = self._cr.fetchone()
        return amount_currency if journal_currency else balance, nb_lines

    def _get_journal_outstanding_payments_account_balance(self, domain=None, date=None):
        ''' Get the outstanding payments balance of the current journal by filtering the journal items using the
        journal's accounts.

        /!\ The current journal is not part of the applied domain. This is the expected behavior since we only want
        a logic based on accounts.

        :param domain:  An additional domain to be applied on the account.move.line model.
        :param date:    The date to be used when performing the currency conversions.
        :return:        The balance expressed in the journal's currency.
        '''
        self.ensure_one()
        self.env['account.move.line'].check_access_rights('read')
        conversion_date = date or fields.Date.context_today(self)

        accounts = self.payment_debit_account_id + self.payment_credit_account_id
        if not accounts:
            return 0.0

        domain = (domain or []) + [
            ('account_id', 'in', tuple(accounts.ids)),
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('move_id.state', '!=', 'cancel'),
            ('reconciled', '=', False),
        ]
        query = self.env['account.move.line']._where_calc(domain)
        tables, where_clause, where_params = query.get_sql()

        self._cr.execute('''
            SELECT
                COUNT(account_move_line.id) AS nb_lines,
                account_move_line.currency_id,
                account.reconcile AS is_account_reconcile,
                SUM(account_move_line.amount_residual) AS amount_residual,
                SUM(account_move_line.balance) AS balance,
                SUM(account_move_line.amount_residual_currency) AS amount_residual_currency,
                SUM(account_move_line.amount_currency) AS amount_currency
            FROM ''' + tables + '''
            JOIN account_account account ON account.id = account_move_line.account_id
            WHERE ''' + where_clause + '''
            GROUP BY account_move_line.currency_id, account.reconcile
        ''', where_params)

        company_currency = self.company_id.currency_id
        journal_currency = self.currency_id if self.currency_id and self.currency_id != company_currency else False
        balance_currency = journal_currency or company_currency

        total_balance = 0.0
        nb_lines = 0
        for res in self._cr.dictfetchall():
            nb_lines += res['nb_lines']

            amount_currency = res['amount_residual_currency'] if res['is_account_reconcile'] else res['amount_currency']
            balance = res['amount_residual'] if res['is_account_reconcile'] else res['balance']

            if res['currency_id'] and journal_currency and res['currency_id'] == journal_currency.id:
                total_balance += amount_currency
            elif journal_currency:
                total_balance += company_currency._convert(balance, balance_currency, self.company_id, conversion_date)
            else:
                total_balance += balance
        return total_balance, nb_lines

    def _get_last_bank_statement(self, domain=None):
        ''' Retrieve the last bank statement created using this journal.
        :param domain:  An additional domain to be applied on the account.bank.statement model.
        :return:        An account.bank.statement record or an empty recordset.
        '''
        self.ensure_one()
        last_statement_domain = (domain or []) + [('journal_id', '=', self.id)]
        last_st_line = self.env['account.bank.statement.line'].search(last_statement_domain, order='date desc, id desc', limit=1)
        return last_st_line.statement_id


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    journal_id = fields.One2many('account.journal', 'bank_account_id', domain=[('type', '=', 'bank')], string='Account Journal', readonly=True,
        help="The accounting journal corresponding to this bank account.")

    @api.constrains('journal_id')
    def _check_journal_id(self):
        for bank in self:
            if len(bank.journal_id) > 1:
                raise ValidationError(_('A bank account can belong to only one journal.'))


#----------------------------------------------------------
# Tax
#----------------------------------------------------------

class AccountTaxGroup(models.Model):
    _name = 'account.tax.group'
    _description = 'Tax Group'
    _order = 'sequence asc'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    property_tax_payable_account_id = fields.Many2one('account.account', company_dependent=True, string='Tax current account (payable)')
    property_tax_receivable_account_id = fields.Many2one('account.account', company_dependent=True, string='Tax current account (receivable)')
    property_advance_tax_payment_account_id = fields.Many2one('account.account', company_dependent=True, string='Advance Tax payment account')

    def _any_is_configured(self, company_id):
        domain = expression.OR([[('property_tax_payable_account_id', '!=', False)],
                                [('property_tax_receivable_account_id', '!=', False)],
                                [('property_advance_tax_payment_account_id', '!=', False)]])
        group_with_config = self.with_company(company_id).search_count(domain)
        return group_with_config > 0


class AccountTax(models.Model):
    _name = 'account.tax'
    _description = 'Tax'
    _order = 'sequence,id'
    _check_company_auto = True

    @api.model
    def _default_tax_group(self):
        return self.env['account.tax.group'].search([], limit=1)

    name = fields.Char(string='Tax Name', required=True)
    type_tax_use = fields.Selection(TYPE_TAX_USE, string='Tax Scope', required=True, default="sale",
        help="Determines where the tax is selectable. Note : 'None' means a tax can't be used by itself, however it can still be used in a group. 'adjustment' is used to perform tax adjustment.")
    amount_type = fields.Selection(default='percent', string="Tax Computation", required=True,
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
    amount = fields.Float(required=True, digits=(16, 4))
    description = fields.Char(string='Label on Invoices')
    price_include = fields.Boolean(string='Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")
    include_base_amount = fields.Boolean(string='Affect Base of Subsequent Taxes', default=False,
        help="If set, taxes which are computed after this one will be computed based on the price tax included.")
    analytic = fields.Boolean(string="Include in Analytic Cost", help="If set, the amount computed by this tax will be assigned to the same analytic account as the invoice line (if any)")
    tax_group_id = fields.Many2one('account.tax.group', string="Tax Group", default=_default_tax_group, required=True)
    # Technical field to make the 'tax_exigibility' field invisible if the same named field is set to false in 'res.company' model
    hide_tax_exigibility = fields.Boolean(string='Hide Use Cash Basis Option', related='company_id.tax_exigibility', readonly=True)
    tax_exigibility = fields.Selection(
        [('on_invoice', 'Based on Invoice'),
         ('on_payment', 'Based on Payment'),
        ], string='Tax Due', default='on_invoice',
        help="Based on Invoice: the tax is due as soon as the invoice is validated.\n"
        "Based on Payment: the tax is due as soon as the payment of the invoice is received.")
    cash_basis_transition_account_id = fields.Many2one(string="Cash Basis Transition Account",
        check_company=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        comodel_name='account.account',
        help="Account used to transition the tax amount for cash basis taxes. It will contain the tax amount as long as the original invoice has not been reconciled ; at reconciliation, this amount cancelled on this account and put on the regular tax account.")
    cash_basis_base_account_id = fields.Many2one(
        'account.account',
        check_company=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        string='Base Tax Received Account',
        help='Account that will be set on lines created in cash basis journal entry and used to keep track of the tax base amount.')
    invoice_repartition_line_ids = fields.One2many(string="Repartition for Invoices", comodel_name="account.tax.repartition.line", inverse_name="invoice_tax_id", copy=True, help="Repartition when the tax is used on an invoice")
    refund_repartition_line_ids = fields.One2many(string="Repartition for Refund Invoices", comodel_name="account.tax.repartition.line", inverse_name="refund_tax_id", copy=True, help="Repartition when the tax is used on a refund")
    country_id = fields.Many2one(string='Country', comodel_name='res.country', related='company_id.country_id', help="Technical field used to restrict the domain of account tags for tax repartition lines created for this tax.")

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, type_tax_use)', 'Tax names must be unique !'),
    ]

    @api.model
    def default_get(self, vals):
        # company_id is added so that we are sure to fetch a default value from it to use in repartition lines, below
        rslt = super(AccountTax, self).default_get(vals + ['company_id'])

        company_id = rslt.get('company_id')
        company = self.env['res.company'].browse(company_id)

        if 'refund_repartition_line_ids' in vals:
            # We write on the related country_id field so that the field is recomputed. Without that, it will stay empty until we save the record.
            rslt['refund_repartition_line_ids'] = [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'country_id': company.country_id.id}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'country_id': company.country_id.id}),
            ]

        if 'invoice_repartition_line_ids' in vals:
            # We write on the related country_id field so that the field is recomputed. Without that, it will stay empty until we save the record.
            rslt['invoice_repartition_line_ids'] = [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'country_id': company.country_id.id}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0, 'tag_ids': [], 'company_id': company_id, 'country_id': company.country_id.id}),
            ]

        return rslt

    def _check_repartition_lines(self, lines):
        self.ensure_one()

        base_line = lines.filtered(lambda x: x.repartition_type == 'base')
        if len(base_line) != 1:
            raise ValidationError(_("Invoice and credit note repartition should each contain exactly one line for the base."))

    @api.constrains('invoice_repartition_line_ids', 'refund_repartition_line_ids')
    def _validate_repartition_lines(self):
        for record in self:
            invoice_repartition_line_ids = record.invoice_repartition_line_ids.sorted()
            refund_repartition_line_ids = record.refund_repartition_line_ids.sorted()
            record._check_repartition_lines(invoice_repartition_line_ids)
            record._check_repartition_lines(refund_repartition_line_ids)

            if len(invoice_repartition_line_ids) != len(refund_repartition_line_ids):
                raise ValidationError(_("Invoice and credit note repartition should have the same number of lines."))

            index = 0
            while index < len(invoice_repartition_line_ids):
                inv_rep_ln = invoice_repartition_line_ids[index]
                ref_rep_ln = refund_repartition_line_ids[index]
                if inv_rep_ln.repartition_type != ref_rep_ln.repartition_type or inv_rep_ln.factor_percent != ref_rep_ln.factor_percent:
                    raise ValidationError(_("Invoice and credit note repartitions should match (same percentages, in the same order)."))
                index += 1

    @api.constrains('children_tax_ids', 'type_tax_use')
    def _check_children_scope(self):
        for tax in self:
            if not tax._check_m2m_recursion('children_tax_ids'):
                raise ValidationError(_("Recursion found for tax '%s'.") % (tax.name,))
            if not all(child.type_tax_use in ('none', tax.type_tax_use) for child in tax.children_tax_ids):
                raise ValidationError(_('The application scope of taxes in a group must be either the same as the group or left empty.'))\

    @api.constrains('company_id')
    def _check_company_consistency(self):
        if not self:
            return

        self.flush(['company_id'])
        self._cr.execute('''
            SELECT line.id
            FROM account_move_line line
            JOIN account_tax tax ON tax.id = line.tax_line_id
            WHERE line.tax_line_id IN %s
            AND line.company_id != tax.company_id

            UNION ALL

            SELECT line.id
            FROM account_move_line_account_tax_rel tax_rel
            JOIN account_tax tax ON tax.id = tax_rel.account_tax_id
            JOIN account_move_line line ON line.id = tax_rel.account_move_line_id
            WHERE tax_rel.account_tax_id IN %s
            AND line.company_id != tax.company_id
        ''', [tuple(self.ids)] * 2)
        if self._cr.fetchone():
            raise UserError(_("You can't change the company of your tax since there are some journal items linked to it."))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {}, name=_("%s (Copy)") % self.name)
        return super(AccountTax, self).copy(default=default)

    def name_get(self):
        if not self._context.get('append_type_to_tax_name'):
            return super(AccountTax, self).name_get()
        tax_type = dict(self._fields['type_tax_use']._description_selection(self.env))
        return [(tax.id, '%s (%s)' % (tax.name, tax_type.get(tax.type_tax_use))) for tax in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """ Returns a list of tuples containing id, name, as internally it is called {def name_get}
            result format: {[(id, name), (id, name), ...]}
        """
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            connector = '&' if operator in expression.NEGATIVE_TERM_OPERATORS else '|'
            domain = [connector, ('description', operator, name), ('name', operator, name)]
        tax_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(tax_ids).with_user(name_get_uid))

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        context = self._context or {}

        if context.get('move_type'):
            if context.get('move_type') in ('out_invoice', 'out_refund'):
                args += [('type_tax_use', '=', 'sale')]
            elif context.get('move_type') in ('in_invoice', 'in_refund'):
                args += [('type_tax_use', '=', 'purchase')]

        if context.get('journal_id'):
            journal = self.env['account.journal'].browse(context.get('journal_id'))
            if journal.type in ('sale', 'purchase'):
                args += [('type_tax_use', '=', journal.type)]

        return super(AccountTax, self)._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)

    @api.onchange('amount')
    def onchange_amount(self):
        if self.amount_type in ('percent', 'division') and self.amount != 0.0 and not self.description:
            self.description = "{0:.4g}%".format(self.amount)

    @api.onchange('amount_type')
    def onchange_amount_type(self):
        if self.amount_type != 'group':
            self.children_tax_ids = [(5,)]
        if self.amount_type == 'group':
            self.description = None

    @api.onchange('price_include')
    def onchange_price_include(self):
        if self.price_include:
            self.include_base_amount = True

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
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
                return math.copysign(quantity, base_amount) * self.amount
            else:
                return quantity * self.amount

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

    def json_friendly_compute_all(self, price_unit, currency_id=None, quantity=1.0, product_id=None, partner_id=None, is_refund=False):
        """ Just converts parameters in browse records and calls for compute_all, because js widgets can't serialize browse records """
        if currency_id:
            currency_id = self.env['res.currency'].browse(currency_id)
        if product_id:
            product_id = self.env['product.product'].browse(product_id)
        if partner_id:
            partner_id = self.env['res.partner'].browse(partner_id)
        return self.compute_all(price_unit, currency=currency_id, quantity=quantity, product=product_id, partner=partner_id, is_refund=is_refund)

    def flatten_taxes_hierarchy(self):
        # Flattens the taxes contained in this recordset, returning all the
        # children at the bottom of the hierarchy, in a recordset, ordered by sequence.
        #   Eg. considering letters as taxes and alphabetic order as sequence :
        #   [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]
        all_taxes = self.env['account.tax']
        for tax in self.sorted(key=lambda r: r.sequence):
            if tax.amount_type == 'group':
                all_taxes += tax.children_tax_ids.flatten_taxes_hierarchy()
            else:
                all_taxes += tax
        return all_taxes

    def get_tax_tags(self, is_refund, repartition_type):
        rep_lines = self.mapped(is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids')
        return rep_lines.filtered(lambda x: x.repartition_type == repartition_type).mapped('tag_ids')

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True):
        """ Returns all information required to apply taxes (in self + their children in case of a tax group).
            We consider the sequence of the parent for group of taxes.
                Eg. considering letters as taxes and alphabetic order as sequence :
                [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]

            'handle_price_include' is used when we need to ignore all tax included in price. If False, it means the
            amount passed to this method will be considered as the base of all computations.

        RETURN: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'total_void'    : 0.0,    # Total with those taxes, that don't have an account set
            'taxes': [{               # One dict for each tax in self and their children
                'id': int,
                'name': str,
                'amount': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': boolean,
            }],
        } """
        if not self:
            company = self.env.company
        else:
            company = self[0].company_id

        # 1) Flatten the taxes.
        taxes = self.flatten_taxes_hierarchy()

        # 2) Avoid mixing taxes having price_include=False && include_base_amount=True
        # with taxes having price_include=True. This use case is not supported as the
        # computation of the total_excluded would be impossible.
        base_excluded_flag = False  # price_include=False && include_base_amount=True
        included_flag = False  # price_include=True
        for tax in taxes:
            if tax.price_include:
                included_flag = True
            elif tax.include_base_amount:
                base_excluded_flag = True
            if base_excluded_flag and included_flag:
                raise UserError(_('Unable to mix any taxes being price included with taxes affecting the base amount but not included in price.'))

        # 3) Deal with the rounding methods
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
        prec = currency.decimal_places

        # In some cases, it is necessary to force/prevent the rounding of the tax and the total
        # amounts. For example, in SO/PO line, we don't want to round the price unit at the
        # precision of the currency.
        # The context key 'round' allows to force the standard behavior.
        round_tax = False if company.tax_calculation_rounding_method == 'round_globally' else True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])

        if not round_tax:
            prec += 5

        # 4) Iterate the taxes in the reversed sequence order to retrieve the initial base of the computation.
        #     tax  |  base  |  amount  |
        # /\ ----------------------------
        # || tax_1 |  XXXX  |          | <- we are looking for that, it's the total_excluded
        # || tax_2 |   ..   |          |
        # || tax_3 |   ..   |          |
        # ||  ...  |   ..   |    ..    |
        #    ----------------------------
        def recompute_base(base_amount, fixed_amount, percent_amount, division_amount):
            # Recompute the new base amount based on included fixed/percent amounts and the current base amount.
            # Example:
            #  tax  |  amount  |   type   |  price_include  |
            # -----------------------------------------------
            # tax_1 |   10%    | percent  |  t
            # tax_2 |   15     |   fix    |  t
            # tax_3 |   20%    | percent  |  t
            # tax_4 |   10%    | division |  t
            # -----------------------------------------------

            # if base_amount = 145, the new base is computed as:
            # (145 - 15) / (1.0 + 30%) * 90% = 130 / 1.3 * 90% = 90
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
        base = currency.round(price_unit * quantity)

        # For the computation of move lines, we could have a negative base value.
        # In this case, compute all with positive values and negate them at the end.
        sign = 1
        if base < 0:
            base = -base
            sign = -1

        # Store the totals to reach when using price_include taxes (only the last price included in row)
        total_included_checkpoints = {}
        i = len(taxes) - 1
        store_included_tax_total = True
        # Keep track of the accumulated included fixed/percent amount.
        incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
        # Store the tax amounts we compute while searching for the total_excluded
        cached_tax_amounts = {}
        if handle_price_include:
            for tax in reversed(taxes):
                tax_repartition_lines = (
                    is_refund
                    and tax.refund_repartition_line_ids
                    or tax.invoice_repartition_line_ids
                ).filtered(lambda x: x.repartition_type == "tax")
                sum_repartition_factor = sum(tax_repartition_lines.mapped("factor"))

                if tax.include_base_amount:
                    base = recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount)
                    incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
                    store_included_tax_total = True
                if tax.price_include or self._context.get('force_price_include'):
                    if tax.amount_type == 'percent':
                        incl_percent_amount += tax.amount * sum_repartition_factor
                    elif tax.amount_type == 'division':
                        incl_division_amount += tax.amount * sum_repartition_factor
                    elif tax.amount_type == 'fixed':
                        incl_fixed_amount += quantity * tax.amount * sum_repartition_factor
                    else:
                        # tax.amount_type == other (python)
                        tax_amount = tax._compute_amount(base, price_unit, quantity, product, partner) * sum_repartition_factor
                        incl_fixed_amount += tax_amount
                        # Avoid unecessary re-computation
                        cached_tax_amounts[i] = tax_amount
                    if store_included_tax_total:
                        total_included_checkpoints[i] = base
                        store_included_tax_total = False
                i -= 1

        total_excluded = currency.round(recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount))

        # 5) Iterate the taxes in the sequence order to compute missing tax amounts.
        # Start the computation of accumulated amounts at the total_excluded value.
        base = total_included = total_void = total_excluded

        taxes_vals = []
        i = 0
        cumulated_tax_included_amount = 0
        for tax in taxes:
            tax_repartition_lines = (is_refund and tax.refund_repartition_line_ids or tax.invoice_repartition_line_ids).filtered(lambda x: x.repartition_type == 'tax')
            sum_repartition_factor = sum(tax_repartition_lines.mapped('factor'))

            #compute the tax_amount
            if (self._context.get('force_price_include') or tax.price_include) and total_included_checkpoints.get(i):
                # We know the total to reach for that tax, so we make a substraction to avoid any rounding issues
                tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount)
                cumulated_tax_included_amount = 0
            else:
                tax_amount = tax.with_context(force_price_include=False)._compute_amount(
                    base, sign * price_unit, quantity, product, partner)

            # Round the tax_amount multiplied by the computed repartition lines factor.
            tax_amount = round(tax_amount, prec)
            factorized_tax_amount = round(tax_amount * sum_repartition_factor, prec)

            if tax.price_include and not total_included_checkpoints.get(i):
                cumulated_tax_included_amount += factorized_tax_amount

            # If the tax affects the base of subsequent taxes, its tax move lines must
            # receive the base tags and tag_ids of these taxes, so that the tax report computes
            # the right total
            subsequent_taxes = self.env['account.tax']
            subsequent_tags = self.env['account.account.tag']
            if tax.include_base_amount:
                subsequent_taxes = taxes[i+1:]
                subsequent_tags = subsequent_taxes.get_tax_tags(is_refund, 'base')

            # Compute the tax line amounts by multiplying each factor with the tax amount.
            # Then, spread the tax rounding to ensure the consistency of each line independently with the factorized
            # amount. E.g:
            #
            # Suppose a tax having 4 x 50% repartition line applied on a tax amount of 0.03 with 2 decimal places.
            # The factorized_tax_amount will be 0.06 (200% x 0.03). However, each line taken independently will compute
            # 50% * 0.03 = 0.01 with rounding. It means there is 0.06 - 0.04 = 0.02 as total_rounding_error to dispatch
            # in lines as 2 x 0.01.
            repartition_line_amounts = [round(tax_amount * line.factor, prec) for line in tax_repartition_lines]
            total_rounding_error = round(factorized_tax_amount - sum(repartition_line_amounts), prec)
            nber_rounding_steps = int(abs(total_rounding_error / currency.rounding))
            rounding_error = round(nber_rounding_steps and total_rounding_error / nber_rounding_steps or 0.0, prec)

            for repartition_line, line_amount in zip(tax_repartition_lines, repartition_line_amounts):

                if nber_rounding_steps:
                    line_amount += rounding_error
                    nber_rounding_steps -= 1

                taxes_vals.append({
                    'id': tax.id,
                    'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
                    'amount': sign * line_amount,
                    'base': round(sign * base, prec),
                    'sequence': tax.sequence,
                    'account_id': tax.cash_basis_transition_account_id.id if tax.tax_exigibility == 'on_payment' else repartition_line.account_id.id,
                    'analytic': tax.analytic,
                    'price_include': tax.price_include or self._context.get('force_price_include'),
                    'tax_exigibility': tax.tax_exigibility,
                    'tax_repartition_line_id': repartition_line.id,
                    'tag_ids': (repartition_line.tag_ids + subsequent_tags).ids,
                    'tax_ids': subsequent_taxes.ids,
                })

                if not repartition_line.account_id:
                    total_void += line_amount

            # Affect subsequent taxes
            if tax.include_base_amount:
                base += factorized_tax_amount

            total_included += factorized_tax_amount
            i += 1

        return {
            'base_tags': taxes.mapped(is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids').filtered(lambda x: x.repartition_type == 'base').mapped('tag_ids').ids,
            'taxes': taxes_vals,
            'total_excluded': sign * total_excluded,
            'total_included': sign * currency.round(total_included),
            'total_void': sign * currency.round(total_void),
        }

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


class AccountTaxRepartitionLine(models.Model):
    _name = "account.tax.repartition.line"
    _description = "Tax Repartition Line"
    _order = 'sequence, repartition_type, id'
    _check_company_auto = True

    factor_percent = fields.Float(string="%", required=True, help="Factor to apply on the account move lines generated from this repartition line, in percents")
    factor = fields.Float(string="Factor Ratio", compute="_compute_factor", help="Factor to apply on the account move lines generated from this repartition line")
    repartition_type = fields.Selection(string="Based On", selection=[('base', 'Base'), ('tax', 'of tax')], required=True, default='tax', help="Base on which the factor will be applied.")
    account_id = fields.Many2one(string="Account",
        comodel_name='account.account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id), ('internal_type', 'not in', ('receivable', 'payable'))]",
        check_company=True,
        help="Account on which to post the tax amount")
    tag_ids = fields.Many2many(string="Tax Grids", comodel_name='account.account.tag', domain=[('applicability', '=', 'taxes')], copy=True)
    invoice_tax_id = fields.Many2one(comodel_name='account.tax',
        check_company=True,
        help="The tax set to apply this repartition on invoices. Mutually exclusive with refund_tax_id")
    refund_tax_id = fields.Many2one(comodel_name='account.tax',
        check_company=True,
        help="The tax set to apply this repartition on refund invoices. Mutually exclusive with invoice_tax_id")
    tax_id = fields.Many2one(comodel_name='account.tax', compute='_compute_tax_id')
    country_id = fields.Many2one(string="Country", comodel_name='res.country', related='company_id.country_id', help="Technical field used to restrict tags domain in form view.")
    company_id = fields.Many2one(string="Company", comodel_name='res.company', compute="_compute_company", store=True, help="The company this repartition line belongs to.")
    sequence = fields.Integer(string="Sequence", default=1, help="The order in which display and match repartition lines. For refunds to work properly, invoice repartition lines should be arranged in the same order as the credit note repartition lines they correspond to.")
    use_in_tax_closing = fields.Boolean(string="Tax Closing Entry")

    @api.onchange('account_id')
    def _on_change_account_id(self):
        if not self.account_id:
            self.use_in_tax_closing = False
        else:
            self.use_in_tax_closing = not(self.account_id.internal_group == 'income' or self.account_id.internal_group == 'expense')

    @api.constrains('invoice_tax_id', 'refund_tax_id')
    def validate_tax_template_link(self):
        for record in self:
            if record.invoice_tax_id and record.refund_tax_id:
                raise ValidationError(_("Tax repartition lines should apply to either invoices or refunds, not both at the same time. invoice_tax_id and refund_tax_id should not be set together."))

    @api.depends('factor_percent')
    def _compute_factor(self):
        for record in self:
            record.factor = record.factor_percent / 100.0

    @api.depends('invoice_tax_id.company_id', 'refund_tax_id.company_id')
    def _compute_company(self):
        for record in self:
            record.company_id = record.invoice_tax_id and record.invoice_tax_id.company_id.id or record.refund_tax_id.company_id.id

    @api.depends('invoice_tax_id', 'refund_tax_id')
    def _compute_tax_id(self):
        for record in self:
            record.tax_id = record.invoice_tax_id or record.refund_tax_id

    @api.onchange('repartition_type')
    def _onchange_repartition_type(self):
        if self.repartition_type == 'base':
            self.account_id = None
