# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import re
import logging

from psycopg2 import sql, DatabaseError

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, mute_logger
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP

_logger = logging.getLogger(__name__)

class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _description = 'Fiscal Position'
    _order = 'sequence'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    sequence = fields.Integer()
    name = fields.Char(string='Fiscal Position', required=True, translate=True)
    active = fields.Boolean(default=True,
        help="By unchecking the active field, you may hide a fiscal position without deleting it.")
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    account_ids = fields.One2many('account.fiscal.position.account', 'position_id', string='Account Mapping', copy=True)
    tax_ids = fields.One2many('account.fiscal.position.tax', 'position_id', string='Tax Mapping', copy=True)
    note = fields.Html('Notes', translate=True, help="Legal mentions that have to be printed on the invoices.")
    auto_apply = fields.Boolean(string='Detect Automatically', help="Apply tax & account mappings on invoices automatically if the matching criterias (VAT/Country) are met.")
    vat_required = fields.Boolean(string='VAT required', help="Apply only if partner has a VAT number.")
    company_country_id = fields.Many2one(string="Company Country", related='company_id.account_fiscal_country_id')
    fiscal_country_codes = fields.Char(string="Company Fiscal Country Code", related='company_country_id.code')
    country_id = fields.Many2one('res.country', string='Country',
        help="Apply only if delivery country matches.")
    country_group_id = fields.Many2one('res.country.group', string='Country Group',
        help="Apply only if delivery country matches the group.")
    state_ids = fields.Many2many('res.country.state', string='Federal States')
    zip_from = fields.Char(string='Zip Range From')
    zip_to = fields.Char(string='Zip Range To')
    # To be used in hiding the 'Federal States' field('attrs' in view side) when selected 'Country' has 0 states.
    states_count = fields.Integer(compute='_compute_states_count')
    foreign_vat = fields.Char(string="Foreign Tax ID", help="The tax ID of your company in the region mapped by this fiscal position.")

    # Technical field used to display a banner on top of foreign vat fiscal positions,
    # in order to ease the instantiation of foreign taxes when possible.
    foreign_vat_header_mode = fields.Selection(
        selection=[('templates_found', "Templates Found"), ('no_template', "No Template")],
        compute='_compute_foreign_vat_header_mode')

    def _compute_states_count(self):
        for position in self:
            position.states_count = len(position.country_id.state_ids)

    @api.depends('foreign_vat', 'country_id')
    def _compute_foreign_vat_header_mode(self):
        for fiscal_position in self:
            if (
                    not fiscal_position.foreign_vat
                    or not fiscal_position.country_id
                    or self.env['account.tax'].search([('country_id', '=', fiscal_position.country_id.id)], limit=1)
            ):
                fiscal_position.foreign_vat_header_mode = False
            else:
                template_code = self.env['account.chart.template']._guess_chart_template(fiscal_position.country_id)
                template = self.env['account.chart.template']._get_chart_template_mapping()[template_code]
                # 'no_template' kept for compatibility in stable. To remove in master
                fiscal_position.foreign_vat_header_mode = 'templates_found' if template['installed'] else 'no_template'

    @api.constrains('zip_from', 'zip_to')
    def _check_zip(self):
        for position in self:
            if position.zip_from and position.zip_to and position.zip_from > position.zip_to:
                raise ValidationError(_('Invalid "Zip Range", please configure it properly.'))

    @api.constrains('country_id', 'state_ids', 'foreign_vat')
    def _validate_foreign_vat_country(self):
        for record in self:
            if record.foreign_vat:
                if record.country_id == record.company_id.account_fiscal_country_id:
                    if record.foreign_vat == record.company_id.vat:
                        raise ValidationError(_("You cannot create a fiscal position within your fiscal country with the same VAT number as the main one set on your company."))

                    if not record.state_ids:
                        if record.company_id.account_fiscal_country_id.state_ids:
                            raise ValidationError(_("You cannot create a fiscal position with a foreign VAT within your fiscal country without assigning it a state."))
                        else:
                            raise ValidationError(_("You cannot create a fiscal position with a foreign VAT within your fiscal country."))

                similar_fpos_domain = [
                    *self.env['account.fiscal.position']._check_company_domain(record.company_id),
                    ('foreign_vat', '!=', False),
                    ('country_id', '=', record.country_id.id),
                    ('id', '!=', record.id),
                ]
                if record.state_ids:
                    similar_fpos_domain.append(('state_ids', 'in', record.state_ids.ids))

                similar_fpos_count = self.env['account.fiscal.position'].search_count(similar_fpos_domain)
                if similar_fpos_count:
                    raise ValidationError(_("A fiscal position with a foreign VAT already exists in this region."))

    def map_tax(self, taxes):
        if not self:
            return taxes
        result = self.env['account.tax']
        for tax in taxes:
            taxes_correspondance = self.tax_ids.filtered(lambda t: t.tax_src_id == tax._origin and (not t.tax_dest_id or t.tax_dest_active))
            result |= taxes_correspondance.tax_dest_id if taxes_correspondance else tax
        return result

    def map_account(self, account):
        for pos in self.account_ids:
            if pos.account_src_id == account:
                return pos.account_dest_id
        return account

    def map_accounts(self, accounts):
        """ Receive a dictionary having accounts in values and try to replace those accounts accordingly to the fiscal position.
        """
        ref_dict = {}
        for line in self.account_ids:
            ref_dict[line.account_src_id] = line.account_dest_id
        for key, acc in accounts.items():
            if acc in ref_dict:
                accounts[key] = ref_dict[acc]
        return accounts

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:
            self.zip_from = self.zip_to = self.country_group_id = False
            self.state_ids = [(5,)]
            self.states_count = len(self.country_id.state_ids)

    @api.onchange('country_group_id')
    def _onchange_country_group_id(self):
        if self.country_group_id:
            self.zip_from = self.zip_to = self.country_id = False
            self.state_ids = [(5,)]

    @api.model
    def _convert_zip_values(self, zip_from='', zip_to=''):
        max_length = max(len(zip_from), len(zip_to))
        if zip_from.isdigit():
            zip_from = zip_from.rjust(max_length, '0')
        if zip_to.isdigit():
            zip_to = zip_to.rjust(max_length, '0')
        return zip_from, zip_to

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            zip_from = vals.get('zip_from')
            zip_to = vals.get('zip_to')
            if zip_from and zip_to:
                vals['zip_from'], vals['zip_to'] = self._convert_zip_values(zip_from, zip_to)
        return super().create(vals_list)

    def write(self, vals):
        zip_from = vals.get('zip_from')
        zip_to = vals.get('zip_to')
        if zip_from or zip_to:
            for rec in self:
                vals['zip_from'], vals['zip_to'] = self._convert_zip_values(zip_from or rec.zip_from, zip_to or rec.zip_to)
        return super(AccountFiscalPosition, self).write(vals)

    @api.model
    def _get_fpos_by_region(self, country_id=False, state_id=False, zipcode=False, vat_required=False):
        if not country_id:
            return False
        base_domain = self._prepare_fpos_base_domain(vat_required)
        null_state_dom = state_domain = [('state_ids', '=', False)]
        null_zip_dom = zip_domain = [('zip_from', '=', False), ('zip_to', '=', False)]
        null_country_dom = [('country_id', '=', False), ('country_group_id', '=', False)]

        if zipcode:
            zip_domain = [('zip_from', '<=', zipcode), ('zip_to', '>=', zipcode)]

        if state_id:
            state_domain = [('state_ids', '=', state_id)]

        domain_country = base_domain + [('country_id', '=', country_id)]
        domain_group = base_domain + [('country_group_id.country_ids', '=', country_id)]

        # Build domain to search records with exact matching criteria
        fpos = self.search(domain_country + state_domain + zip_domain, limit=1)
        # return records that fit the most the criteria, and fallback on less specific fiscal positions if any can be found
        if not fpos and state_id:
            fpos = self.search(domain_country + null_state_dom + zip_domain, limit=1)
        if not fpos and zipcode:
            fpos = self.search(domain_country + state_domain + null_zip_dom, limit=1)
        if not fpos and state_id and zipcode:
            fpos = self.search(domain_country + null_state_dom + null_zip_dom, limit=1)

        # fallback: country group with no state/zip range
        if not fpos:
            fpos = self.search(domain_group + null_state_dom + null_zip_dom, limit=1)

        if not fpos:
            # Fallback on catchall (no country, no group)
            fpos = self.search(base_domain + null_country_dom, limit=1)
        return fpos

    def _get_vat_valid(self, delivery, company=None):
        """ Hook for determining VAT validity with more complex VAT requirements """
        return bool(delivery.vat)

    def _prepare_fpos_base_domain(self, vat_required):
        return [
            *self._check_company_domain(self.env.company),
            ('auto_apply', '=', True),
            ('vat_required', '=', vat_required),
        ]

    @api.model
    def _get_fiscal_position(self, partner, delivery=None):
        """
        :return: fiscal position found (recordset)
        :rtype: :class:`account.fiscal.position`
        """
        if not partner:
            return self.env['account.fiscal.position']

        company = self.env.company
        intra_eu = vat_exclusion = False
        if company.vat and partner.vat:
            eu_country_codes = set(self.env.ref('base.europe').country_ids.mapped('code'))
            intra_eu = company.vat[:2] in eu_country_codes and partner.vat[:2] in eu_country_codes
            vat_exclusion = company.vat[:2] == partner.vat[:2]

        # If company and partner have the same vat prefix (and are both within the EU), use invoicing
        if not delivery or (intra_eu and vat_exclusion):
            delivery = partner

        # partner manually set fiscal position always win
        manual_fiscal_position = (
            delivery.with_company(company).property_account_position_id
            or partner.with_company(company).property_account_position_id
        )
        if manual_fiscal_position:
            return manual_fiscal_position

        # First search only matching VAT positions
        vat_valid = self._get_vat_valid(delivery, company)
        fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, vat_valid)

        # Then if VAT required found no match, try positions that do not require it
        if not fp and vat_valid:
            fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, False)

        return fp or self.env['account.fiscal.position']

    def action_create_foreign_taxes(self):
        self.ensure_one()
        template_code = self.env['account.chart.template']._guess_chart_template(self.country_id)
        template = self.env['account.chart.template']._get_chart_template_mapping()[template_code]
        if not template['installed']:
            localization_module = self.env['ir.module.module'].search([('name', '=', template['module'])])
            localization_module.sudo().button_immediate_install()
        self.env["account.chart.template"]._instantiate_foreign_taxes(self.country_id, self.company_id)

class AccountFiscalPositionTax(models.Model):
    _name = 'account.fiscal.position.tax'
    _description = 'Tax Mapping of Fiscal Position'
    _rec_name = 'position_id'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='position_id.company_id', store=True)
    tax_src_id = fields.Many2one('account.tax', string='Tax on Product', required=True, check_company=True)
    tax_dest_id = fields.Many2one('account.tax', string='Tax to Apply', check_company=True)
    tax_dest_active = fields.Boolean(related="tax_dest_id.active")

    _sql_constraints = [
        ('tax_src_dest_uniq',
         'unique (position_id,tax_src_id,tax_dest_id)',
         'A tax fiscal position could be defined only one time on same taxes.')
    ]


class AccountFiscalPositionAccount(models.Model):
    _name = 'account.fiscal.position.account'
    _description = 'Accounts Mapping of Fiscal Position'
    _rec_name = 'position_id'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='position_id.company_id', store=True)
    account_src_id = fields.Many2one('account.account', string='Account on Product',
        check_company=True, required=True,
        domain="[('deprecated', '=', False)]")
    account_dest_id = fields.Many2one('account.account', string='Account to Use Instead',
        check_company=True, required=True,
        domain="[('deprecated', '=', False)]")

    _sql_constraints = [
        ('account_src_dest_uniq',
         'unique (position_id,account_src_id,account_dest_id)',
         'An account fiscal position could be defined only one time on same accounts.')
    ]


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    fiscal_country_codes = fields.Char(compute='_compute_fiscal_country_codes')

    @api.depends('company_id')
    @api.depends_context('allowed_company_ids')
    def _compute_fiscal_country_codes(self):
        for record in self:
            allowed_companies = record.company_id or self.env.companies
            record.fiscal_country_codes = ",".join(allowed_companies.mapped('account_fiscal_country_id.code'))

    @property
    def _order(self):
        res = super()._order
        partner_search_mode = self.env.context.get('res_partner_search_mode')
        if partner_search_mode not in ('customer', 'supplier'):
            return res
        order_by_field = f"{partner_search_mode}_rank DESC"
        return '%s, %s' % (order_by_field, res) if res else order_by_field

    @api.depends_context('company')
    def _credit_debit_get(self):
        if not self.ids:
            self.debit = False
            self.credit = False
            return
        tables, where_clause, where_params = self.env['account.move.line']._where_calc([
            ('parent_state', '=', 'posted'),
            ('company_id', 'child_of', self.env.company.root_id.id)
        ]).get_sql()

        where_params = [tuple(self.ids)] + where_params
        if where_clause:
            where_clause = 'AND ' + where_clause
        self.env['account.move.line'].flush_model(
            ['account_id', 'amount_residual', 'company_id', 'parent_state', 'partner_id', 'reconciled']
        )
        self.env['account.account'].flush_model(['account_type'])
        self._cr.execute("""SELECT account_move_line.partner_id, a.account_type, SUM(account_move_line.amount_residual)
                      FROM """ + tables + """
                      LEFT JOIN account_account a ON (account_move_line.account_id=a.id)
                      WHERE a.account_type IN ('asset_receivable','liability_payable')
                      AND account_move_line.partner_id IN %s
                      AND account_move_line.reconciled IS NOT TRUE
                      """ + where_clause + """
                      GROUP BY account_move_line.partner_id, a.account_type
                      """, where_params)
        treated = self.browse()
        for pid, type, val in self._cr.fetchall():
            partner = self.browse(pid)
            if type == 'asset_receivable':
                partner.credit = val
                if partner not in treated:
                    partner.debit = False
                    treated |= partner
            elif type == 'liability_payable':
                partner.debit = -val
                if partner not in treated:
                    partner.credit = False
                    treated |= partner
        remaining = (self - treated)
        remaining.debit = False
        remaining.credit = False

    @api.depends_context('company')
    def _compute_credit_to_invoice(self):
        # To be overridden in Sales
        self.credit_to_invoice = False

    def _asset_difference_search(self, account_type, operator, operand):
        if operator not in ('<', '=', '>', '>=', '<='):
            return []
        if not isinstance(operand, (float, int)):
            return []
        sign = 1
        if account_type == 'liability_payable':
            sign = -1
        res = self._cr.execute(f'''
            SELECT aml.partner_id
              FROM res_partner partner
         LEFT JOIN account_move_line aml ON aml.partner_id = partner.id
              JOIN account_move move ON move.id = aml.move_id
              JOIN res_company line_company ON line_company.id = aml.company_id
        RIGHT JOIN account_account acc ON aml.account_id = acc.id
             WHERE acc.account_type = %s
               AND NOT acc.deprecated
               AND SPLIT_PART(line_company.parent_path, '/', 1)::int = %s
               AND move.state = 'posted'
          GROUP BY aml.partner_id
            HAVING %s * COALESCE(SUM(aml.amount_residual), 0) {operator} %s''',
            (account_type, self.env.company.root_id.id, sign, operand)
        )
        res = self._cr.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [r[0] for r in res])]

    @api.model
    def _credit_search(self, operator, operand):
        return self._asset_difference_search('asset_receivable', operator, operand)

    @api.model
    def _debit_search(self, operator, operand):
        return self._asset_difference_search('liability_payable', operator, operand)

    def _invoice_total(self):
        self.total_invoiced = 0
        if not self.ids:
            return True

        all_partners_and_children = {}
        all_partner_ids = []
        for partner in self.filtered('id'):
            # price_total is in the company currency
            all_partners_and_children[partner] = self.with_context(active_test=False).search([('id', 'child_of', partner.id)]).ids
            all_partner_ids += all_partners_and_children[partner]

        domain = [
            ('partner_id', 'in', all_partner_ids),
            ('state', 'not in', ['draft', 'cancel']),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
        ]
        price_totals = self.env['account.invoice.report']._read_group(domain, ['partner_id'], ['price_subtotal:sum'])
        for partner, child_ids in all_partners_and_children.items():
            partner.total_invoiced = sum(price_subtotal_sum for partner, price_subtotal_sum in price_totals if partner.id in child_ids)

    @api.depends('credit')
    def _compute_days_sales_outstanding(self):
        commercial_partners = {
            commercial_partner: (invoice_date_min, amount_total_signed_sum)
            for commercial_partner, invoice_date_min, amount_total_signed_sum in self.env['account.move']._read_group(
                domain=[
                    ('state', 'not in', ['draft', 'cancel']),
                    ('move_type', 'in', self.env["account.move"].get_sale_types(include_receipts=True)),
                    ('company_id', '=', self.env.company.id),
                    ('commercial_partner_id', 'in', self.commercial_partner_id.ids),
                ],
                groupby=['commercial_partner_id'],
                aggregates=['invoice_date:min', 'amount_total_signed:sum'],
            )
        }
        for partner in self:
            oldest_invoice_date, total_invoiced_tax_included = commercial_partners.get(partner, (fields.Date.context_today(self), 0))
            days_since_oldest_invoice = (fields.Date.context_today(self) - oldest_invoice_date).days
            partner.days_sales_outstanding = ((partner.credit / total_invoiced_tax_included) * days_since_oldest_invoice) if total_invoiced_tax_included else 0

    def _compute_journal_item_count(self):
        AccountMoveLine = self.env['account.move.line']
        for partner in self:
            partner.journal_item_count = AccountMoveLine.search_count([('partner_id', '=', partner.id)])

    def _compute_has_unreconciled_entries(self):
        for partner in self:
            # Avoid useless work if has_unreconciled_entries is not relevant for this partner
            if not partner.active or not partner.is_company and partner.parent_id:
                partner.has_unreconciled_entries = False
                continue
            self.env.cr.execute(
                """ SELECT 1 FROM(
                        SELECT
                            p.last_time_entries_checked AS last_time_entries_checked,
                            MAX(l.write_date) AS max_date
                        FROM
                            account_move_line l
                            RIGHT JOIN account_account a ON (a.id = l.account_id)
                            RIGHT JOIN res_partner p ON (l.partner_id = p.id)
                        WHERE
                            p.id = %s
                            AND EXISTS (
                                SELECT 1
                                FROM account_move_line l
                                WHERE l.account_id = a.id
                                AND l.partner_id = p.id
                                AND l.amount_residual > 0
                            )
                            AND EXISTS (
                                SELECT 1
                                FROM account_move_line l
                                WHERE l.account_id = a.id
                                AND l.partner_id = p.id
                                AND l.amount_residual < 0
                            )
                        GROUP BY p.last_time_entries_checked
                    ) as s
                    WHERE (last_time_entries_checked IS NULL OR max_date > last_time_entries_checked)
                """, (partner.id,))
            partner.has_unreconciled_entries = self.env.cr.rowcount == 1

    def mark_as_reconciled(self):
        self.env['account.partial.reconcile'].check_access_rights('write')
        return self.sudo().write({'last_time_entries_checked': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

    def _get_company_currency(self):
        for partner in self:
            if partner.company_id:
                partner.currency_id = partner.sudo().company_id.currency_id
            else:
                partner.currency_id = self.env.company.currency_id

    credit = fields.Monetary(compute='_credit_debit_get', search=_credit_search,
        string='Total Receivable', help="Total amount this customer owes you.",
        groups='account.group_account_invoice,account.group_account_readonly')
    credit_to_invoice = fields.Monetary(
        compute='_compute_credit_to_invoice',
        groups='account.group_account_invoice,account.group_account_readonly'
    )
    credit_limit = fields.Float(
        string='Credit Limit', help='Credit limit specific to this partner.',
        groups='account.group_account_invoice,account.group_account_readonly',
        company_dependent=True, copy=False, readonly=False)
    use_partner_credit_limit = fields.Boolean(
        string='Partner Limit', groups='account.group_account_invoice,account.group_account_readonly',
        compute='_compute_use_partner_credit_limit', inverse='_inverse_use_partner_credit_limit')
    show_credit_limit = fields.Boolean(
        default=lambda self: self.env.company.account_use_credit_limit,
        compute='_compute_show_credit_limit', groups='account.group_account_invoice,account.group_account_readonly')
    days_sales_outstanding = fields.Float(
        string='Days Sales Outstanding (DSO)',
        help='[(Total Receivable/Total Revenue) * number of days since the first invoice] for this customer',
        compute='_compute_days_sales_outstanding')
    debit = fields.Monetary(
        compute='_credit_debit_get', search=_debit_search, string='Total Payable',
        help="Total amount you have to pay to this vendor.",
        groups='account.group_account_invoice,account.group_account_readonly')
    debit_limit = fields.Monetary('Payable Limit')
    total_invoiced = fields.Monetary(compute='_invoice_total', string="Total Invoiced",
        groups='account.group_account_invoice,account.group_account_readonly')
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
        string="Currency") # currency of amount currency
    journal_item_count = fields.Integer(compute='_compute_journal_item_count', string="Journal Items")
    property_account_payable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Payable",
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the payable account for the current partner",
        required=True)
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Receivable",
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        required=True)
    property_account_position_id = fields.Many2one('account.fiscal.position', company_dependent=True,
        string="Fiscal Position",
        help="The fiscal position determines the taxes/accounts used for this contact.")
    property_payment_term_id = fields.Many2one('account.payment.term', company_dependent=True,
        string='Customer Payment Terms',
        help="This payment term will be used instead of the default one for sales orders and customer invoices")
    property_supplier_payment_term_id = fields.Many2one('account.payment.term', company_dependent=True,
        string='Vendor Payment Terms',
        help="This payment term will be used instead of the default one for purchase orders and vendor bills")
    ref_company_ids = fields.One2many('res.company', 'partner_id',
        string='Companies that refers to partner')
    has_unreconciled_entries = fields.Boolean(compute='_compute_has_unreconciled_entries',
        help="The partner has at least one unreconciled debit and credit since last time the invoices & payments matching was performed.")
    last_time_entries_checked = fields.Datetime(
        string='Latest Invoices & Payments Matching Date', readonly=True, copy=False,
        help='Last time the invoices & payments matching was performed for this partner. '
             'It is set either if there\'s not at least an unreconciled debit and an unreconciled credit '
             'or if you click the "Done" button.')
    invoice_ids = fields.One2many('account.move', 'partner_id', string='Invoices', readonly=True, copy=False)
    contract_ids = fields.One2many('account.analytic.account', 'partner_id', string='Partner Contracts', readonly=True)
    bank_account_count = fields.Integer(compute='_compute_bank_count', string="Bank")
    trust = fields.Selection([('good', 'Good Debtor'), ('normal', 'Normal Debtor'), ('bad', 'Bad Debtor')], string='Degree of trust you have in this debtor', default='normal', company_dependent=True)
    invoice_warn = fields.Selection(WARNING_MESSAGE, 'Invoice', help=WARNING_HELP, default="no-message")
    invoice_warn_msg = fields.Text('Message for Invoice')
    # Computed fields to order the partners as suppliers/customers according to the
    # amount of their generated incoming/outgoing account moves
    supplier_rank = fields.Integer(default=0, copy=False)
    customer_rank = fields.Integer(default=0, copy=False)

    # Technical field holding the amount partners that share the same account number as any set on this partner.
    duplicated_bank_account_partners_count = fields.Integer(
        compute='_compute_duplicated_bank_account_partners_count',
    )

    def _compute_bank_count(self):
        bank_data = self.env['res.partner.bank']._read_group([('partner_id', 'in', self.ids)], ['partner_id'], ['__count'])
        mapped_data = {partner.id: count for partner, count in bank_data}
        for partner in self:
            partner.bank_account_count = mapped_data.get(partner.id, 0)

    def _get_duplicated_bank_accounts(self):
        self.ensure_one()
        if not self.bank_ids:
            return self.env['res.partner.bank']
        domains = []
        for bank in self.bank_ids:
            domains.append([('acc_number', '=', bank.acc_number), ('bank_id', '=', bank.bank_id.id)])
        domain = expression.OR(domains)
        if self.company_id:
            domain = expression.AND([domain, [('company_id', 'in', (False, self.company_id.id))]])
        domain = expression.AND([domain, [('partner_id', '!=', self._origin.id)]])
        return self.env['res.partner.bank'].search(domain)

    @api.depends('bank_ids')
    def _compute_duplicated_bank_account_partners_count(self):
        for partner in self:
            partner.duplicated_bank_account_partners_count = len(partner._get_duplicated_bank_accounts())

    @api.depends_context('company')
    def _compute_use_partner_credit_limit(self):
        for partner in self:
            company_limit = self.env['ir.property']._get('credit_limit', 'res.partner')
            partner.use_partner_credit_limit = partner.credit_limit != company_limit

    def _inverse_use_partner_credit_limit(self):
        for partner in self:
            if not partner.use_partner_credit_limit:
                partner.credit_limit = self.env['ir.property']._get('credit_limit', 'res.partner')

    @api.depends_context('company')
    def _compute_show_credit_limit(self):
        for partner in self:
            partner.show_credit_limit = self.env.company.account_use_credit_limit

    def _find_accounting_partner(self, partner):
        ''' Find the partner for which the accounting entries will be created '''
        return partner.commercial_partner_id

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + \
            ['debit_limit', 'property_account_payable_id', 'property_account_receivable_id', 'property_account_position_id',
             'property_payment_term_id', 'property_supplier_payment_term_id', 'last_time_entries_checked', 'credit_limit']

    def action_view_partner_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        all_child = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])
        action['domain'] = [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('partner_id', 'in', all_child.ids)
        ]
        action['context'] = {'default_move_type': 'out_invoice', 'move_type': 'out_invoice', 'journal_type': 'sale', 'search_default_unpaid': 1}
        return action

    def action_view_partner_with_same_bank(self):
        self.ensure_one()
        bank_partners = self._get_duplicated_bank_accounts()
        # Open a list view or form view of the partner(s) with the same bank accounts
        if self.duplicated_bank_account_partners_count == 1:
            action_vals = {
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'form',
                'res_id': bank_partners.partner_id.id,
                'views': [(False, 'form')],
            }
        else:
            action_vals = {
                'name': _("Partners"),
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'tree,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('id', 'in', bank_partners.partner_id.ids)],
            }

        return action_vals

    def _has_invoice(self, partner_domain):
        self.ensure_one()
        invoice = self.env['account.move'].sudo().search(
            expression.AND([
                partner_domain,
                [
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('state', '=', 'posted'),
                ]
            ]),
            limit=1
        )
        return bool(invoice)

    def _can_edit_name(self):
        """ Can't edit `name` if there is (non draft) issued invoices. """
        return super()._can_edit_name() and not self._has_invoice(
            [('partner_id', '=', self.id)]
        )

    def can_edit_vat(self):
        """ Can't edit `vat` if there is (non draft) issued invoices. """
        return super().can_edit_vat() and not self._has_invoice(
            [('partner_id', 'child_of', self.commercial_partner_id.id)]
        )

    @api.model_create_multi
    def create(self, vals_list):
        search_partner_mode = self.env.context.get('res_partner_search_mode')
        is_customer = search_partner_mode == 'customer'
        is_supplier = search_partner_mode == 'supplier'
        if search_partner_mode:
            for vals in vals_list:
                if is_customer and 'customer_rank' not in vals:
                    vals['customer_rank'] = 1
                elif is_supplier and 'supplier_rank' not in vals:
                    vals['supplier_rank'] = 1
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_partner_in_account_move(self):
        """
        Prevent the deletion of a partner "Individual", child of a company if:
        - partner in 'account.move'
        - state: all states (draft and posted)
        """
        moves = self.sudo().env['account.move'].search_count([
            ('partner_id', 'in', self.ids),
            ('state', 'in', ['draft', 'posted']),
        ])
        if moves:
            raise UserError(_("The partner cannot be deleted because it is used in Accounting"))

    def _increase_rank(self, field, n=1):
        if self.ids and field in ['customer_rank', 'supplier_rank']:
            try:
                with self.env.cr.savepoint(flush=False), mute_logger('odoo.sql_db'):
                    query = sql.SQL("""
                        SELECT {field} FROM res_partner WHERE ID IN %(partner_ids)s FOR NO KEY UPDATE NOWAIT;
                        UPDATE res_partner SET {field} = {field} + %(n)s
                        WHERE id IN %(partner_ids)s
                    """).format(field=sql.Identifier(field))
                    self.env.cr.execute(query, {'partner_ids': tuple(self.ids), 'n': n})
                    self.invalidate_recordset([field])
            except DatabaseError as e:
                # 55P03 LockNotAvailable
                # 40001 SerializationFailure
                if e.pgcode not in ('55P03', '40001'):
                    raise e
                _logger.debug('Another transaction already locked partner rows. Cannot update partner ranks.')

    @api.model
    def _run_vat_test(self, vat_number, default_country, partner_is_company=True):
        """ Checks a VAT number syntactically to ensure its validity upon saving.

        :param vat_number: a string with the VAT number to check.
        :param default_country: a res.country object
        :param partner_is_company: True if the partner is a company, else False.
            .. deprecated:: 16.0
                Will be removed in 16.2

        :return: The country code (in lower case) of the country the VAT number
                 was validated for, if it was validated. False if it could not be validated
                 against the provided or guessed country. None if no country was available
                 for the check, and no conclusion could be made with certainty.
        """
        return default_country.code.lower()

    @api.model
    def _build_vat_error_message(self, country_code, wrong_vat, record_label):
        """ Prepare an error message for the VAT number that failed validation

        :param country_code: string of lowercase country code
        :param wrong_vat: the vat number that was validated
        :param record_label: a string to desribe the record that failed a VAT validation check

        :return: The error message string
        """
        return ""

    @api.model
    def get_partner_localisation_fields_required_to_invoice(self, country_id):
        """ Returns the list of fields that needs to be filled when creating an invoice for the selected country.
        This is required for some flows that would allow a user to request an invoice from the portal.
        Using these, we can get their information and dynamically create form inputs based for the fields required legally for the company country_id.
        The returned fields must be of type ir.model.fields in order to handle translations

        :param country_id: The country for which we want the fields.
        :return: an array of ir.model.fields for which the user should provide values.
        """
        return []

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    @api.model
    def _retrieve_partner_with_vat(self, vat, extra_domain):
        if not vat:
            return None

        # Sometimes, the vat is specified with some whitespaces.
        normalized_vat = vat.replace(' ', '')
        country_prefix = re.match('^[a-zA-Z]{2}|^', vat).group()

        partner = self.env['res.partner'].search(extra_domain + [('vat', 'in', (normalized_vat, vat))], limit=2)

        # Try to remove the country code prefix from the vat.
        if not partner and country_prefix:
            partner = self.env['res.partner'].search(extra_domain + [
                ('vat', 'in', (normalized_vat[2:], vat[2:])),
                ('country_id.code', '=', country_prefix.upper()),
            ], limit=2)

            # The country could be not specified on the partner.
            if not partner:
                partner = self.env['res.partner'].search(extra_domain + [
                    ('vat', 'in', (normalized_vat[2:], vat[2:])),
                    ('country_id', '=', False),
                ], limit=2)

        # The vat could be a string of alphanumeric values without country code but with missing zeros at the
        # beginning.
        if not partner:
            try:
                vat_only_numeric = str(int(re.sub(r'^\D{2}', '', normalized_vat) or 0))
            except ValueError:
                vat_only_numeric = None

            if vat_only_numeric:
                if country_prefix:
                    vat_prefix_regex = f'({country_prefix})?'
                else:
                    vat_prefix_regex = '([A-z]{2})?'
                query = self.env['res.partner']._search(extra_domain + [('active', '=', True)], limit=2)
                query.add_where("res_partner.vat ~ %s", ['^%s0*%s$' % (vat_prefix_regex, vat_only_numeric)])
                query_str, params = query.select()
                self._cr.execute(query_str, params)
                partner_rows = self._cr.fetchall() or []
                if len(partner_rows) == 1:
                    partner = self.env['res.partner'].browse(partner_rows[0][0])

        return partner

    @api.model
    def _retrieve_partner_with_phone_mail(self, phone, mail, extra_domain):
        domains = []
        if phone:
            domains.append([('phone', '=', phone)])
            domains.append([('mobile', '=', phone)])
        if mail:
            domains.append([('email', '=', mail)])

        if not domains:
            return None

        domain = expression.OR(domains)
        if extra_domain:
            domain = expression.AND([domain, extra_domain])
        return self.env['res.partner'].search(domain, limit=2)

    @api.model
    def _retrieve_partner_with_name(self, name, extra_domain):
        if not name:
            return None
        return self.env['res.partner'].search([('name', 'ilike', name)] + extra_domain, limit=2)

    def _retrieve_partner(self, name=None, phone=None, mail=None, vat=None, domain=None, company=None):
        '''Search all partners and find one that matches one of the parameters.
        :param name:    The name of the partner.
        :param phone:   The phone or mobile of the partner.
        :param mail:    The mail of the partner.
        :param vat:     The vat number of the partner.
        :param domain:  An extra domain to apply.
        :param company: The company of the partner.
        :returns:       A partner or an empty recordset if not found.
        '''

        def search_with_vat(extra_domain):
            return self._retrieve_partner_with_vat(vat, extra_domain)

        def search_with_phone_mail(extra_domain):
            return self._retrieve_partner_with_phone_mail(phone, mail, extra_domain)

        def search_with_name(extra_domain):
            return self._retrieve_partner_with_name(name, extra_domain)

        def search_with_domain(extra_domain):
            if not domain:
                return None
            return self.env['res.partner'].search(domain + extra_domain, limit=1)

        for search_method in (search_with_vat, search_with_domain, search_with_phone_mail, search_with_name):
            for extra_domain in (
                [*self.env['res.partner']._check_company_domain(company or self.env.company), ('company_id', '!=', False)],
                [('company_id', '=', False)],
            ):
                partner = search_method(extra_domain)
                if partner and len(partner) == 1:
                    return partner
        return self.env['res.partner']

    def _merge_method(self, destination, source):
        """
        Prevent merging partners that are linked to already hashed journal items.
        """
        if self.env['account.move.line'].sudo().search([('move_id.inalterable_hash', '!=', False), ('partner_id', 'in', source.ids)], limit=1):
            raise UserError(_('Partners that are used in hashed entries cannot be merged.'))
        return super()._merge_method(destination, source)

    def _deduce_country_code(self):
        """ deduce the country code based on the information available.
        we have three cases:
        - country_code is BE but the VAT number starts with FR, the country code is FR, not BE
        - if a country-specific field is set (e.g. the codice_fiscale), that country is used for the country code
        - if the VAT number has no ISO country code, use the country_code in that case.
        """
        self.ensure_one()

        country_code = self.country_code
        if self.vat and self.vat[:2].isalpha():
            country_code = self.vat[:2].upper()
        return country_code
