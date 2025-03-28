# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import time
import re
import logging

from psycopg2 import errors as pgerrors

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, mute_logger
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.tools import SQL, unique
from odoo.addons.base_vat.models.res_partner import _ref_vat

_logger = logging.getLogger(__name__)


_ref_company_registry = {
    'jp': '7000012050002',
}


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
    account_map = fields.Binary(compute='_compute_account_map')
    tax_ids = fields.One2many('account.fiscal.position.tax', 'position_id', string='Tax Mapping', copy=True)
    tax_map = fields.Binary(compute='_compute_tax_map')
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
    foreign_vat = fields.Char(string="Foreign Tax ID", inverse="_inverse_foreign_vat", help="The tax ID of your company in the region mapped by this fiscal position.")

    # Technical field used to display a banner on top of foreign vat fiscal positions,
    # in order to ease the instantiation of foreign taxes when possible.
    foreign_vat_header_mode = fields.Selection(
        selection=[('templates_found', "Templates Found"), ('no_template', "No Template")],
        compute='_compute_foreign_vat_header_mode')

    def _inverse_foreign_vat(self):
        # Hook for extension
        pass

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

    @api.depends('tax_ids.tax_src_id', 'tax_ids.tax_dest_id')
    def _compute_tax_map(self):
        for position in self:
            tax_map = defaultdict(list)
            for tl in position.tax_ids:
                if tl.tax_dest_id:
                    tax_map[tl.tax_src_id.id].append(tl.tax_dest_id.id)
                else:
                    tax_map[tl.tax_src_id.id]  # map to an empty list
            position.tax_map = dict(tax_map)

    @api.depends('account_ids.account_src_id', 'account_ids.account_dest_id')
    def _compute_account_map(self):
        for position in self:
            position.account_map = {al.account_src_id.id: al.account_dest_id.id for al in position.account_ids}

    @api.constrains('zip_from', 'zip_to')
    def _check_zip(self):
        for position in self:
            if bool(position.zip_from) != bool(position.zip_to) or position.zip_from > position.zip_to:
                raise ValidationError(_('Invalid "Zip Range", You have to configure both "From" and "To" values for the zip range and "To" should be greater than "From".'))

    @api.constrains('country_id', 'country_group_id', 'state_ids', 'foreign_vat')
    def _validate_foreign_vat_country(self):
        for record in self:
            if record.foreign_vat:
                if record.country_id == record.company_id.account_fiscal_country_id:
                    if not record.state_ids:
                        if record.company_id.account_fiscal_country_id.state_ids:
                            raise ValidationError(_("You cannot create a fiscal position with a foreign VAT within your fiscal country without assigning it a state."))
                if record.country_group_id and record.country_id:
                    if record.country_id not in record.country_group_id.country_ids:
                        raise ValidationError(_("You cannot create a fiscal position with a country outside of the selected country group."))

                similar_fpos_domain = [
                    *self.env['account.fiscal.position']._check_company_domain(record.company_id),
                    ('foreign_vat', '!=', False),
                    ('id', '!=', record.id),
                ]

                if record.country_group_id:
                    foreign_vat_country = self.country_group_id.country_ids.filtered(lambda c: c.code == record.foreign_vat[:2].upper())
                    if not foreign_vat_country:
                        raise ValidationError(_("The country code of the foreign VAT number does not match any country in the group."))
                    similar_fpos_domain += [('country_group_id', '=', record.country_group_id.id), ('country_id', '=', foreign_vat_country.id)]
                elif record.country_id:
                    similar_fpos_domain += [('country_id', '=', record.country_id.id), ('country_group_id', '=', False)]

                if record.state_ids:
                    similar_fpos_domain.append(('state_ids', 'in', record.state_ids.ids))
                else:
                    similar_fpos_domain.append(('state_ids', '=', False))

                similar_fpos_count = self.env['account.fiscal.position'].search_count(similar_fpos_domain)
                if similar_fpos_count:
                    raise ValidationError(_("A fiscal position with a foreign VAT already exists in this region."))

    def map_tax(self, taxes):
        return self.env['account.tax'].browse(unique(
            tax_id
            for tax in taxes
            for tax_id in (self.tax_map or {}).get(tax.id, [tax.id])
        ))

    def map_account(self, account):
        return self.env['account.account'].browse((self.account_map or {}).get(account.id, account.id))

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:
            self.zip_from = self.zip_to = False
            self.state_ids = [(5,)]
            self.states_count = len(self.country_id.state_ids)

    @api.onchange('country_group_id')
    def _onchange_country_group_id(self):
        if self.country_group_id:
            self.zip_from = self.zip_to = False
            self.state_ids = [(5,)]

    @api.model
    def _convert_zip_values(self, zip_from='', zip_to=''):
        if zip_from and zip_to:
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

    def _get_vat_valid(self, delivery, company=None):
        """ Hook for determining VAT validity with more complex VAT requirements """
        return bool(delivery.vat)

    def _get_fpos_ranking_functions(self, partner):
        """Get comparison functions to rank fiscal positions.

        All functions are applied to the fiscal position and return a value.
        These values are taken in order to build a tuple that will be the comparator
        value between fiscal positions.

        If the value returned by one of the function is falsy, the fiscal position is
        filtered out and not even considered for the ranking.

        :param partner: the partner to consider for the ranking of the fiscal positions
        :type partner: :class:`res.partner`
        :return: a list of tuples with a name and the function to apply. The name is only
            used to facilitate extending the comparators.
        :rtype: list[tuple[str, function]
        """
        return [
            ('vat_required', lambda fpos: (
                not fpos.vat_required
                or (self._get_vat_valid(partner, self.env.company) and 2)
            )),
            ('company_id', lambda fpos: len(fpos.company_id.parent_ids)),
            ('zipcode', lambda fpos:(
                not (fpos.zip_from and fpos.zip_to)
                or (partner.zip and (fpos.zip_from <= partner.zip <= fpos.zip_to) and 2)
            )),
            ('state_id', lambda fpos: (
                not fpos.state_ids
                or (partner.state_id in fpos.state_ids and 2)
            )),
            ('country_id', lambda fpos: (
                not fpos.country_id
                or (partner.country_id == fpos.country_id and 2)
            )),
            ('country_group', lambda fpos: (
                not fpos.country_group_id
                or (partner.country_id in fpos.country_group_id.country_ids and 2)
            )),
            ('sequence', lambda fpos: -(fpos.sequence or 0.1)),  # do not filter out sequence=0, priority to lowest sequence in `max` method
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

        if not partner.country_id:
            return self.env['account.fiscal.position']

        # Search for a auto applied fiscal position matching the partner
        ranking_subfunctions = self._get_fpos_ranking_functions(delivery)
        def ranking_function(fpos):
            return tuple(rank[1](fpos) for rank in ranking_subfunctions)

        all_auto_apply_fpos = self.search(self._check_company_domain(self.env.company) + [('auto_apply', '=', True)])
        fpo_with_ranking = ((fpos, ranking_function(fpos)) for fpos in all_auto_apply_fpos)
        valid_auto_apply_fpos = filter(lambda x: all(x[1]), fpo_with_ranking)
        return max(
            valid_auto_apply_fpos,
            key=lambda x: x[1],
            default=(self.env['account.fiscal.position'], False)
        )[0]

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
    partner_vat_placeholder = fields.Char(compute='_compute_partner_vat_placeholder')
    partner_company_registry_placeholder = fields.Char(compute='_compute_partner_company_registry_placeholder')

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
        query = self.env['account.move.line']._where_calc([
            ('parent_state', '=', 'posted'),
            ('company_id', 'child_of', self.env.company.root_id.id)
        ])
        self.env['account.move.line'].flush_model(
            ['account_id', 'amount_residual', 'company_id', 'parent_state', 'partner_id', 'reconciled']
        )
        self.env['account.account'].flush_model(['account_type'])
        sql = SQL("""
            SELECT account_move_line.partner_id, a.account_type, SUM(account_move_line.amount_residual)
            FROM %s
            LEFT JOIN account_account a ON (account_move_line.account_id=a.id)
            WHERE a.account_type IN ('asset_receivable','liability_payable')
            AND account_move_line.partner_id IN %s
            AND account_move_line.reconciled IS NOT TRUE
            AND %s
            GROUP BY account_move_line.partner_id, a.account_type
            """,
            query.from_clause,
            tuple(self.ids),
            query.where_clause or SQL("TRUE"),
        )
        treated = self.browse()
        for pid, account_type, val in self.env.execute_query(sql):
            partner = self.browse(pid)
            if account_type == 'asset_receivable':
                partner.credit = val
                if partner not in treated:
                    partner.debit = False
                    treated |= partner
            elif account_type == 'liability_payable':
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

    def _get_company_currency(self):
        for partner in self:
            if partner.company_id:
                partner.currency_id = partner.sudo().company_id.currency_id
            else:
                partner.currency_id = self.env.company.currency_id

    def _default_display_invoice_template_pdf_report_id(self):
        available_templates_count = self.env['ir.actions.report'].search_count([('is_invoice_report', '=', True)], limit=2)
        return available_templates_count > 1

    name = fields.Char(tracking=True)
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
        compute='_compute_use_partner_credit_limit', inverse='_inverse_use_partner_credit_limit',
        help='Set a value greater than 0.0 to activate a credit limit check')
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
        ondelete='restrict')
    property_account_receivable_id = fields.Many2one('account.account', company_dependent=True,
        string="Account Receivable",
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
        help="This account will be used instead of the default one as the receivable account for the current partner",
        ondelete='restrict')
    property_account_position_id = fields.Many2one('account.fiscal.position', company_dependent=True,
        string="Fiscal Position",
        help="The fiscal position determines the taxes/accounts used for this contact.")
    property_payment_term_id = fields.Many2one('account.payment.term', company_dependent=True,
        string='Customer Payment Terms',
        help="This payment term will be used instead of the default one for sales orders and customer invoices",
        ondelete='restrict')
    property_supplier_payment_term_id = fields.Many2one('account.payment.term', company_dependent=True,
        string='Vendor Payment Terms',
        help="This payment term will be used instead of the default one for purchase orders and vendor bills")
    ref_company_ids = fields.One2many('res.company', 'partner_id',
        string='Companies that refers to partner')
    supplier_invoice_count = fields.Integer(compute='_compute_supplier_invoice_count', string='# Vendor Bills')
    invoice_ids = fields.One2many('account.move', 'partner_id', string='Invoices', readonly=True, copy=False)
    contract_ids = fields.One2many('account.analytic.account', 'partner_id', string='Partner Contracts', readonly=True)
    bank_account_count = fields.Integer(compute='_compute_bank_count', string="Bank")
    trust = fields.Selection([('good', 'Good Debtor'), ('normal', 'Normal Debtor'), ('bad', 'Bad Debtor')], string='Degree of trust you have in this debtor', company_dependent=True)
    ignore_abnormal_invoice_date = fields.Boolean(company_dependent=True)
    ignore_abnormal_invoice_amount = fields.Boolean(company_dependent=True)
    invoice_warn = fields.Selection(WARNING_MESSAGE, 'Invoice', help=WARNING_HELP, default="no-message")
    invoice_warn_msg = fields.Text('Message for Invoice')
    invoice_sending_method = fields.Selection(
        string="Invoice sending",
        selection=[
            ('manual', 'Download'),
            ('email', 'by Email'),
        ],
        company_dependent=True,
    )
    invoice_edi_format = fields.Selection(
        string="eInvoice format",
        selection=[],  # to extend
        compute='_compute_invoice_edi_format',
        inverse='_inverse_invoice_edi_format',
        compute_sudo=True,
    )
    invoice_edi_format_store = fields.Char(company_dependent=True)
    display_invoice_edi_format = fields.Boolean(default=lambda self: len(self._fields['invoice_edi_format'].selection), store=False)
    invoice_template_pdf_report_id = fields.Many2one(
        comodel_name='ir.actions.report',
        string='Invoice template',
        domain="[('is_invoice_report', '=', True)]",
        readonly=False,
        store=True,
    )
    display_invoice_template_pdf_report_id = fields.Boolean(default=_default_display_invoice_template_pdf_report_id, store=False)
    # Computed fields to order the partners as suppliers/customers according to the
    # amount of their generated incoming/outgoing account moves
    supplier_rank = fields.Integer(default=0, copy=False)
    customer_rank = fields.Integer(default=0, copy=False)
    autopost_bills = fields.Selection(
        selection=[('always', 'Always'), ('ask', 'Ask after 3 validations without edits'), ('never', 'Never')],
        string='Auto-post bills',
        help="Automatically post bills for this trusted partner",
        default='ask',
        required=True,
    )

    # Technical field holding the amount partners that share the same account number as any set on this partner.
    duplicated_bank_account_partners_count = fields.Integer(
        compute='_compute_duplicated_bank_account_partners_count',
    )
    is_coa_installed = fields.Boolean(store=False, default=lambda partner: bool(partner.env.company.chart_template))

    property_outbound_payment_method_line_id = fields.Many2one(
        comodel_name='account.payment.method.line',
        company_dependent=True,
        domain=lambda self: [('payment_type', '=', 'outbound'), ('company_id', '=', self.env.company.id)],
        help="Preferred payment method when buying from this vendor. This will be set by default on all"
             " outgoing payments created for this vendor",
    )

    property_inbound_payment_method_line_id = fields.Many2one(
        comodel_name='account.payment.method.line',
        company_dependent=True,
        domain=lambda self: [('payment_type', '=', 'inbound'), ('company_id', '=', self.env.company.id)],
        help="Preferred payment method when selling to this customer. This will be set by default on all"
             " incoming payments created for this customer",
    )

    def _compute_bank_count(self):
        bank_data = self.env['res.partner.bank']._read_group([('partner_id', 'in', self.ids)], ['partner_id'], ['__count'])
        mapped_data = {partner.id: count for partner, count in bank_data}
        for partner in self:
            partner.bank_account_count = mapped_data.get(partner.id, 0)

    def _compute_supplier_invoice_count(self):
        # retrieve all children partners and prefetch 'parent_id' on them
        all_partners = self.with_context(active_test=False).search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )
        supplier_invoice_groups = self.env['account.move']._read_group(
            domain=[('partner_id', 'in', all_partners.ids),
                    *self.env['account.move']._check_company_domain(self.env.company),
                    ('move_type', 'in', ('in_invoice', 'in_refund'))],
            groupby=['partner_id'], aggregates=['__count']
        )
        self_ids = set(self._ids)

        self.supplier_invoice_count = 0
        for partner, count in supplier_invoice_groups:
            while partner:
                if partner.id in self_ids:
                    partner.supplier_invoice_count += count
                partner = partner.parent_id

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

    @api.depends_context('company')
    def _compute_invoice_edi_format(self):
        for partner in self:
            if partner.commercial_partner_id.invoice_edi_format_store == 'none':
                partner.invoice_edi_format = False
            else:
                partner.invoice_edi_format = partner.commercial_partner_id.invoice_edi_format_store or partner.commercial_partner_id._get_suggested_invoice_edi_format()

    def _inverse_invoice_edi_format(self):
        for partner in self:
            if partner.invoice_edi_format == partner._get_suggested_invoice_edi_format():
                partner.invoice_edi_format_store = False
            elif not partner.invoice_edi_format:
                partner.invoice_edi_format_store = 'none'
            else:
                partner.invoice_edi_format_store = partner.invoice_edi_format

    @api.depends('bank_ids')
    def _compute_duplicated_bank_account_partners_count(self):
        for partner in self:
            partner.duplicated_bank_account_partners_count = len(partner._get_duplicated_bank_accounts())

    @api.depends_context('company')
    def _compute_use_partner_credit_limit(self):
        company_limit = self._fields['credit_limit'].get_company_dependent_fallback(self)
        for partner in self:
            partner.use_partner_credit_limit = partner.credit_limit != company_limit

    def _inverse_use_partner_credit_limit(self):
        company_limit = self._fields['credit_limit'].get_company_dependent_fallback(self)
        for partner in self:
            if not partner.use_partner_credit_limit:
                partner.credit_limit = company_limit

    @api.depends_context('company')
    def _compute_show_credit_limit(self):
        for partner in self:
            partner.show_credit_limit = self.env.company.account_use_credit_limit

    def _get_suggested_invoice_edi_format(self):
        # TO OVERRIDE
        self.ensure_one()
        return False

    def _find_accounting_partner(self, partner):
        ''' Find the partner for which the accounting entries will be created '''
        return partner.commercial_partner_id

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + \
            ['debit_limit', 'property_account_payable_id', 'property_account_receivable_id', 'property_account_position_id',
             'property_payment_term_id', 'property_supplier_payment_term_id', 'credit_limit']

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
                'view_mode': 'list,form',
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
                    self.env.execute_query(SQL("""
                        SELECT %(field)s FROM res_partner WHERE ID IN %(partner_ids)s FOR NO KEY UPDATE NOWAIT;
                        UPDATE res_partner SET %(field)s = %(field)s + %(n)s
                        WHERE id IN %(partner_ids)s
                        """,
                        field=SQL.identifier(field),
                        partner_ids=tuple(self.ids),
                        n=n,
                    ))
                    self.invalidate_recordset([field])
                    self.modified([field])
            except (pgerrors.LockNotAvailable, pgerrors.SerializationFailure):
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
                Partner = self.env['res.partner']
                query = Partner._search(extra_domain + [('active', '=', True)], limit=2)
                query.add_where(SQL(
                    "%s ~ %s",
                    Partner._field_to_sql(Partner._table, 'vat'),
                    f'^{vat_prefix_regex}0*{vat_only_numeric}$',
                ))
                partner_row = list(query)
                if partner_row and len(partner_row) == 1:
                    partner = Partner.browse(partner_row[0])

        return partner

    @api.model
    def _retrieve_partner_with_phone_email(self, phone, email, extra_domain):
        domains = []
        if phone:
            domains.append([('phone', '=', phone)])
            domains.append([('mobile', '=', phone)])
        if email:
            domains.append([('email', '=', email)])

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

    def _retrieve_partner(self, name=None, phone=None, email=None, vat=None, domain=None, company=None):
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
            return self._retrieve_partner_with_phone_email(phone, email, extra_domain)

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

                # The VAT should be a sufficiently distinctive criterion
                if partner and search_method == search_with_vat:
                    return partner[:1]
                if partner and len(partner) == 1:
                    return partner
        return self.env['res.partner']

    def _merge_method(self, destination, source):
        """
        Prevent merging partners that are linked to already hashed journal items.
        """
        if self.env['account.move.line'].sudo().search_count([('move_id.inalterable_hash', '!=', False), ('partner_id', 'in', source.ids)], limit=1):
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

    @api.depends('country_id')
    def _compute_partner_vat_placeholder(self):
        for partner in self:
            placeholder = _("/ if not applicable")
            if partner.country_id:
                expected_vat = _ref_vat.get(partner.country_id.code.lower())
                if expected_vat:
                    placeholder = _("%s, or / if not applicable", expected_vat)

            partner.partner_vat_placeholder = placeholder

    @api.depends('country_id')
    def _compute_partner_company_registry_placeholder(self):
        """ Provides a dynamic placeholder on the company registry field for countries that may need it.
        Add your country and the value you want in the _ref_company_registry map.
        """
        for partner in self:
            country_code = partner.country_id.code or ''
            partner.partner_company_registry_placeholder = _ref_company_registry.get(country_code.lower(), '')
