# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from collections import defaultdict

from odoo import models, fields, api, _, osv
from odoo.exceptions import ValidationError, UserError

FIGURE_TYPE_SELECTION_VALUES = [
    ('monetary', "Monetary"),
    ('percentage', "Percentage"),
    ('integer', "Integer"),
    ('float', "Float"),
    ('date', "Date"),
    ('datetime', "Datetime"),
    ('none', "No Formatting"),
]

DOMAIN_REGEX = re.compile(r'(-?sum)\((.*)\)')

class AccountReport(models.Model):
    _name = "account.report"
    _description = "Accounting Report"

    #  CORE ==========================================================================================================================================

    name = fields.Char(string="Name", required=True, translate=True)
    line_ids = fields.One2many(string="Lines", comodel_name='account.report.line', inverse_name='report_id')
    column_ids = fields.One2many(string="Columns", comodel_name='account.report.column', inverse_name='report_id')
    root_report_id = fields.Many2one(string="Root Report", comodel_name='account.report', help="The report this report is a variant of.")
    variant_report_ids = fields.One2many(string="Variants", comodel_name='account.report', inverse_name='root_report_id')
    chart_template_id = fields.Many2one(string="Chart of Accounts", comodel_name='account.chart.template')
    country_id = fields.Many2one(string="Country", comodel_name='res.country')
    only_tax_exigible = fields.Boolean(
        string="Only Tax Exigible Lines",
        compute=lambda x: x._compute_report_option_filter('only_tax_exigible'), readonly=False, store=True, depends=['root_report_id'],
    )
    availability_condition = fields.Selection(
        string="Availability",
        selection=[('country', "Country Matches"), ('coa', "Chart of Accounts Matches"), ('always', "Always")],
        compute='_compute_default_availability_condition', readonly=False, store=True,
    )
    load_more_limit = fields.Integer(string="Load More Limit")
    search_bar = fields.Boolean(string="Search Bar")

    default_opening_date_filter = fields.Selection(
        string="Default Opening",
        selection=[
            ('this_year', "This Year"),
            ('this_quarter', "This Quarter"),
            ('this_month', "This Month"),
            ('today', "Today"),
            ('last_month', "Last Month"),
            ('last_quarter', "Last Quarter"),
            ('last_year', "Last Year"),
        ],
        compute=lambda x: x._compute_report_option_filter('default_opening_date_filter', 'last_month'),
        readonly=False, store=True, depends=['root_report_id'],
    )

    #  FILTERS =======================================================================================================================================
    # Those fields control the display of menus on the report

    filter_multi_company = fields.Selection(
        string="Multi-Company",
        selection=[('disabled', "Disabled"), ('selector', "Use Company Selector"), ('tax_units', "Use Tax Units")],
        compute=lambda x: x._compute_report_option_filter('filter_multi_company', 'disabled'), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_date_range = fields.Boolean(
        string="Date Range",
        compute=lambda x: x._compute_report_option_filter('filter_date_range', True), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_show_draft = fields.Boolean(
        string="Draft Entries",
        compute=lambda x: x._compute_report_option_filter('filter_show_draft', True), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_unreconciled = fields.Boolean(
        string="Unreconciled Entries",
        compute=lambda x: x._compute_report_option_filter('filter_unreconciled', False), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_unfold_all = fields.Boolean(
        string="Unfold All",
        compute=lambda x: x._compute_report_option_filter('filter_unfold_all'), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_period_comparison = fields.Boolean(
        string="Period Comparison",
        compute=lambda x: x._compute_report_option_filter('filter_period_comparison', True), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_growth_comparison = fields.Boolean(
        string="Growth Comparison",
        compute=lambda x: x._compute_report_option_filter('filter_growth_comparison', True), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_journals = fields.Boolean(
        string="Journals",
        compute=lambda x: x._compute_report_option_filter('filter_journals'), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_analytic = fields.Boolean(
        string="Analytic Filter",
        compute=lambda x: x._compute_report_option_filter('filter_analytic'), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_hierarchy = fields.Selection(
        string="Account Groups",
        selection=[('by_default', "Enabled by Default"), ('optional', "Optional"), ('never', "Never")],
        compute=lambda x: x._compute_report_option_filter('filter_hierarchy', 'optional'), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_account_type = fields.Boolean(
        string="Account Types",
        compute=lambda x: x._compute_report_option_filter('filter_account_type'), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_partner = fields.Boolean(
        string="Partners",
        compute=lambda x: x._compute_report_option_filter('filter_partner'), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_fiscal_position = fields.Boolean(
        string="Filter Multivat",
        compute=lambda x: x._compute_report_option_filter('filter_fiscal_position'), readonly=False, store=True, depends=['root_report_id'],
    )

    def _compute_report_option_filter(self, field_name, default_value=False):
        # We don't depend on the different filter fields on the root report, as we don't want a manual change on it to be reflected on all the reports
        # using it as their root (would create confusion). The root report filters are only used as some kind of default values.
        for report in self:
            if report.root_report_id:
                report[field_name] = report.root_report_id[field_name]
            else:
                report[field_name] = default_value

    @api.depends('root_report_id', 'country_id')
    def _compute_default_availability_condition(self):
        for report in self:
            if report.root_report_id:
                report.availability_condition = 'country'
            else:
                report.availability_condition = 'always'

    @api.constrains('root_report_id')
    def _validate_root_report_id(self):
        for report in self:
            if report.root_report_id.root_report_id:
                raise ValidationError(_("Only a report without a root report of its own can be selected as root report."))

    def write(self, vals):
        # Overridden so that changing the country of a report also creates new tax tags if necessary, or updates the country
        # of existing tags, if they aren't shared with another report.
        if 'country_id' in vals:
            impacted_reports = self.filtered(lambda x: x.country_id.id != vals['country_id'])
            tax_tags_expressions = impacted_reports.line_ids.expression_ids.filtered(lambda x: x.engine == 'tax_tags')

            for expression in tax_tags_expressions:
                tax_tags = self.env['account.account.tag']._get_tax_tags(expression.formula, expression.report_line_id.report_id.country_id.id)
                tag_reports = tax_tags._get_related_tax_report_expressions().report_line_id.report_id

                if all(report in self for report in tag_reports):
                    # Only reports in self are using these tags; let's change their country
                    tax_tags.write({'country_id': vals['country_id']})
                else:
                    # Another report uses these tags as well; let's keep them and create new tags in the target country
                    # if they don't exist yet.
                    existing_tax_tags = self.env['account.account.tag']._get_tax_tags(expression.formula, vals['country_id'])
                    if not existing_tax_tags:
                        tag_vals = self.env['account.report.expression']._get_tags_create_vals(expression.formula, vals['country_id'])
                        self.env['account.account.tag'].create(tag_vals)

        return super().write(vals)

    def copy(self, default=None):
        '''Copy the whole financial report hierarchy by duplicating each line recursively.

        :param default: Default values.
        :return: The copied account.report record.
        '''
        self.ensure_one()
        if default is None:
            default = {}
        default['name'] = self._get_copied_name()
        copied_report = super().copy(default=default)
        code_mapping = {}
        for line in self.line_ids.filtered(lambda x: not x.parent_id):
            line._copy_hierarchy(copied_report, code_mapping=code_mapping)
        for column in self.column_ids:
            column.copy({'report_id': copied_report.id})
        return copied_report

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_variant(self):
        if self.variant_report_ids:
            raise UserError(_("You can't delete a report that has variants."))

    def _get_copied_name(self):
        '''Return a copied name of the account.report record by adding the suffix (copy) at the end
        until the name is unique.

        :return: an unique name for the copied account.report
        '''
        self.ensure_one()
        name = self.name + ' ' + _('(copy)')
        while self.search_count([('name', '=', name)]) > 0:
            name += ' ' + _('(copy)')
        return name

    @api.depends('name', 'country_id')
    def name_get(self):
        result = []
        for report in self:
            result.append((report.id, report.name + (f' ({report.country_id.code})' if report.country_id else '')))
        return result


class AccountReportLine(models.Model):
    _name = "account.report.line"
    _description = "Accounting Report Line"
    _order = 'sequence, id'

    name = fields.Char(string="Name", translate=True, required=True)
    expression_ids = fields.One2many(string="Expressions", comodel_name='account.report.expression', inverse_name='report_line_id')
    report_id = fields.Many2one(
        string="Parent Report",
        comodel_name='account.report',
        compute='_compute_report_id',
        store=True,
        readonly=False,
        required=True,
        recursive=True,
        precompute=True,
        ondelete='cascade'
    )
    hierarchy_level = fields.Integer(
        string="Level",
        compute='_compute_hierarchy_level',
        store=True,
        readonly=False,
        recursive=True,
        required=True,
        precompute=True,
    )
    parent_id = fields.Many2one(string="Parent Line", comodel_name='account.report.line', ondelete='set null')
    children_ids = fields.One2many(string="Child Lines", comodel_name='account.report.line', inverse_name='parent_id')
    groupby = fields.Char(string="Group By", help="Comma-separated list of fields from account.move.line (Journal Item). When set, this line will generate sublines grouped by those keys.")
    sequence = fields.Integer(string="Sequence")
    code = fields.Char(string="Code", help="Unique identifier for this line.")
    foldable = fields.Boolean(string="Foldable", help="By default, we always unfold the lines that can be. If this is checked, the line won't be unfolded by default, and a folding button will be displayed.")
    print_on_new_page = fields.Boolean('Print On New Page', help='When checked this line and everything after it will be printed on a new page.')
    action_id = fields.Many2one(string="Action", comodel_name='ir.actions.actions', help="Setting this field will turn the line into a link, executing the action when clicked.")
    hide_if_zero = fields.Boolean(string="Hide if Zero", help="This line and its children will be hidden when all of their columns are 0.")
    domain_formula = fields.Char(string="Domain Formula Shortcut", help="Internal field to shorten expression_ids creation for the domain engine", inverse='_inverse_domain_formula', store=False)
    account_codes_formula = fields.Char(string="Account Codes Formula Shortcut", help="Internal field to shorten expression_ids creation for the account_codes engine", inverse='_inverse_account_codes_formula', store=False)
    aggregation_formula = fields.Char(string="Aggregation Formula Shortcut", help="Internal field to shorten expression_ids creation for the aggregation engine", inverse='_inverse_aggregation_formula', store=False)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', "A report line with the same code already exists."),
    ]

    @api.depends('parent_id.hierarchy_level')
    def _compute_hierarchy_level(self):
        for report_line in self:
            if report_line.parent_id:
                report_line.hierarchy_level = report_line.parent_id.hierarchy_level + 2
            else:
                report_line.hierarchy_level = 1

    @api.depends('parent_id.report_id')
    def _compute_report_id(self):
        for report_line in self:
            if report_line.parent_id:
                report_line.report_id = report_line.parent_id.report_id

    @api.constrains('parent_id')
    def _validate_groupby_no_child(self):
        for report_line in self:
            if report_line.parent_id.groupby:
                raise ValidationError(_("A line cannot have both children and a groupby value (line '%s').", report_line.parent_id.name))

    @api.constrains('expression_ids', 'groupby')
    def _validate_formula(self):
        for expression in self.expression_ids:
            if expression.engine == 'aggregation' and expression.report_line_id.groupby:
                raise ValidationError(_(
                    "Groupby feature isn't supported by aggregation engine. Please remove the groupby value on '%s'",
                    expression.report_line_id.display_name,
                ))

    def _copy_hierarchy(self, copied_report, parent=None, code_mapping=None):
        ''' Copy the whole hierarchy from this line by copying each line children recursively and adapting the
        formulas with the new copied codes.

        :param copied_report: The copy of the report.
        :param parent: The parent line in the hierarchy (a copy of the original parent line).
        :param code_mapping: A dictionary keeping track of mapping old_code -> new_code
        '''
        self.ensure_one()

        copied_line = self.copy({
            'report_id': copied_report.id,
            'parent_id': parent and parent.id,
            'code': self.code and self._get_copied_code(),
        })

        # Keep track of old_code -> new_code in a mutable dict
        if code_mapping is None:
            code_mapping = {}
        if self.code:
            code_mapping[self.code] = copied_line.code

        # Copy children
        for line in self.children_ids:
            line._copy_hierarchy(copied_report, parent=copied_line, code_mapping=code_mapping)

        # Update aggregation expressions, so that they use the copied lines
        for expression in self.expression_ids:
            copy_defaults = {'report_line_id': copied_line.id}

            if expression.engine == 'aggregation':
                copied_formula = f" {expression.formula} " # Add spaces so that the lookahead/lookbehind of the regex can work (we can't do a | in those)
                for old_code, new_code in code_mapping.items():
                    copied_formula = re.sub(f"(?<=\\W){old_code}(?=\\W)", new_code, copied_formula)
                copy_defaults['formula'] = copied_formula.strip() # Remove the spaces introduced for lookahead/lookbehind

            expression.copy(copy_defaults)

    def _get_copied_code(self):
        '''Look for an unique copied code.

        :return: an unique code for the copied account.report.line
        '''
        self.ensure_one()
        code = self.code + '_COPY'
        while self.search_count([('code', '=', code)]) > 0:
            code += '_COPY'
        return code

    def _inverse_domain_formula(self):
        self._create_report_expression(engine='domain')

    def _inverse_aggregation_formula(self):
        self._create_report_expression(engine='aggregation')

    def _inverse_account_codes_formula(self):
        self._create_report_expression(engine='account_codes')

    def _create_report_expression(self, engine):
        # create account.report.expression for each report line based on the formula provided to each
        # engine-related field. This makes xmls a bit shorter
        vals_list = []
        for report_line in self:
            if engine == 'domain' and report_line.domain_formula:
                subformula, formula = DOMAIN_REGEX.match(report_line.domain_formula or '').groups()
                # Resolve the calls to ref(), to mimic the fact those formulas are normally given with an eval="..." in XML
                formula = re.sub(r'''\bref\((?P<quote>['"])(?P<xmlid>.+?)(?P=quote)\)''', lambda m: str(self.env.ref(m['xmlid']).id), formula)
            elif engine == 'account_codes' and report_line.account_codes_formula:
                subformula, formula = None, report_line.account_codes_formula
            elif engine == 'aggregation' and report_line.aggregation_formula:
                subformula, formula = None, report_line.aggregation_formula
            else:
                continue

            vals = {
                'report_line_id': report_line.id,
                'label': 'balance',
                'engine': engine,
                'formula': formula.lstrip(' \t\n'),  # Avoid IndentationError in evals
                'subformula': subformula
            }
            if report_line.expression_ids:
                # expressions already exists, update the first expression with the right engine
                # since syntactic sugar aren't meant to be used with multiple expressions
                for expression in report_line.expression_ids:
                    if expression.engine == engine:
                        expression.write(vals)
                        break
            else:
                # else prepare batch creation
                vals_list.append(vals)

        if vals_list:
            self.env['account.report.expression'].create(vals_list)


class AccountReportExpression(models.Model):
    _name = "account.report.expression"
    _description = "Accounting Report Expression"
    _rec_name = 'report_line_name'

    report_line_id = fields.Many2one(string="Report Line", comodel_name='account.report.line', required=True, ondelete='cascade')
    report_line_name = fields.Char(string="Report Line Name", related="report_line_id.name")
    label = fields.Char(string="Label", required=True)
    engine = fields.Selection(
        string="Computation Engine",
        selection=[
            ('domain', "Odoo Domain"),
            ('tax_tags', "Tax Tags"),
            ('aggregation', "Aggregate Other Formulas"),
            ('account_codes', "Prefix of Account Codes"),
            ('external', "External Value"),
            ('custom', "Custom Python Function"),
        ],
        required=True
    )
    formula = fields.Char(string="Formula", required=True)
    subformula = fields.Char(string="Subformula")
    date_scope = fields.Selection(
        string="Date Scope",
        selection=[
            ('from_beginning', 'From the very start'),
            ('from_fiscalyear', 'From the start of the fiscal year'),
            ('to_beginning_of_fiscalyear', 'At the beginning of the fiscal year'),
            ('to_beginning_of_period', 'At the beginning of the period'),
            ('normal', 'According to each type of account'),
            ('strict_range', 'Strictly on the given dates'),
            ('previous_tax_period', "From previous tax period")
        ],
        required=True,
        default='strict_range',
    )
    figure_type = fields.Selection(string="Figure Type", selection=FIGURE_TYPE_SELECTION_VALUES)
    green_on_positive = fields.Boolean(string="Is Growth Good when Positive", default=True)
    blank_if_zero = fields.Boolean(string="Blank if Zero", help="When checked, 0 values will not show when displaying this expression's value.")
    auditable = fields.Boolean(string="Auditable", store=True, readonly=False, compute='_compute_auditable')

    # Carryover fields
    carryover_target = fields.Char(
        string="Carry Over To",
        help="Formula in the form line_code.expression_label. This allows setting the target of the carryover for this expression "
             "(on a _carryover_*-labeled expression), in case it is different from the parent line. 'custom' is also allowed as value"
             " in case the carryover destination requires more complex logic."
    )

    @api.depends('engine')
    def _compute_auditable(self):
        auditable_engines = self._get_auditable_engines()
        for expression in self:
            expression.auditable = expression.engine in auditable_engines

    def _get_auditable_engines(self):
        return {'tax_tags', 'domain', 'account_codes', 'external', 'aggregation'}

    def _strip_formula(self, vals):
        if 'formula' in vals and isinstance(vals['formula'], str):
            vals['formula'] = re.sub(r'\s+', ' ', vals['formula'].strip())

    @api.model_create_multi
    def create(self, vals_list):
        # Overridden so that we create the corresponding account.account.tag objects when instantiating an expression
        # with engine 'tax_tags'.
        for vals in vals_list:
            self._strip_formula(vals)

        result = super().create(vals_list)

        for expression in result:
            tag_name = expression.formula if expression.engine == 'tax_tags' else None
            if tag_name:
                country = expression.report_line_id.report_id.country_id
                existing_tags = self.env['account.account.tag']._get_tax_tags(tag_name, country.id)

                if not existing_tags:
                    tag_vals = self._get_tags_create_vals(tag_name, country.id)
                    self.env['account.account.tag'].create(tag_vals)

        return result

    def write(self, vals):
        if 'formula' not in vals:
            return super().write(vals)

        self._strip_formula(vals)

        tax_tags_expressions = self.filtered(lambda x: x.engine == 'tax_tags')
        former_formulas_by_country = defaultdict(lambda: [])
        for expr in tax_tags_expressions:
            former_formulas_by_country[expr.report_line_id.report_id.country_id].append(expr.formula)

        result = super().write(vals)

        for country, former_formulas_list in former_formulas_by_country.items():
            for former_formula in former_formulas_list:
                new_tax_tags = self.env['account.account.tag']._get_tax_tags(vals['formula'], country.id)

                if not new_tax_tags:
                    # If new tags already exist, nothing to do ; else, we must create them or update existing tags.
                    former_tax_tags = self.env['account.account.tag']._get_tax_tags(former_formula, country.id)

                    if former_tax_tags and all(tag_expr in self for tag_expr in former_tax_tags._get_related_tax_report_expressions()):
                        # If we're changing the formula of all the expressions using that tag, rename the tag
                        positive_tags, negative_tags = former_tax_tags.sorted(lambda x: x.tax_negate)
                        positive_tags.name, negative_tags.name = f"+{vals['formula']}", f"-{vals['formula']}"
                    else:
                        # Else, create a new tag. Its the compute functions will make sure it is properly linked to the expressions
                        tag_vals = self.env['account.report.expression']._get_tags_create_vals(vals['formula'], country.id)
                        self.env['account.account.tag'].create(tag_vals)

        return result

    def name_get(self):
        return [(expr.id, f'{expr.report_line_name} [{expr.label}]') for expr in self]

    def _expand_aggregations(self):
        """Return self and its full aggregation expression dependency"""
        result = self

        to_expand = self.filtered(lambda x: x.engine == 'aggregation')
        while to_expand:
            domains = []

            for candidate_expr in to_expand:
                labels_by_code = candidate_expr._get_aggregation_terms_details()

                cross_report_domain = []
                if candidate_expr.subformula != 'cross_report':
                    cross_report_domain = [('report_line_id.report_id', '=', candidate_expr.report_line_id.report_id.id)]

                for line_code, expr_labels in labels_by_code.items():
                    dependency_domain = [('report_line_id.code', '=', line_code), ('label', 'in', tuple(expr_labels))] + cross_report_domain
                    domains.append(dependency_domain)

            sub_expressions = self.env['account.report.expression'].search(osv.expression.OR(domains))
            to_expand = sub_expressions.filtered(lambda x: x.engine == 'aggregation' and x not in result)
            result |= sub_expressions

        return result

    def _get_aggregation_terms_details(self):
        """ Computes the details of each aggregation expression in self, and returns them in the form of a single dict aggregating all the results.

        Example of aggregation details:
        formula 'A.balance + B.balance + A.other'
        will return: {'A': {'balance', 'other'}, 'B': {'balance'}}
        """
        totals_by_code = defaultdict(set)
        for expression in self:
            if expression.engine != 'aggregation':
                raise UserError(_("Cannot get aggregation details from a line not using 'aggregation' engine"))

            expression_terms = re.split('[-+/*]', re.sub(r'[\s()]', '', expression.formula))
            for term in expression_terms:
                if term and not re.match(r'^([0-9]*[.])?[0-9]*$', term): # term might be empty if the formula contains a negative term
                    line_code, total_name = term.split('.')
                    totals_by_code[line_code].add(total_name)

        return totals_by_code

    def _get_matching_tags(self):
        """ Returns all the signed account.account.tags records whose name matches any of the formulas of the tax_tags expressions contained in self.
        """
        tag_expressions = self.filtered(lambda x: x.engine == 'tax_tags')
        if not tag_expressions:
            return self.env['account.account.tag']

        or_domains = []
        for tag_expression in tag_expressions:
            country = tag_expression.report_line_id.report_id.country_id
            or_domains.append(self.env['account.account.tag']._get_tax_tags_domain(tag_expression.formula, country.id))

        return self.env['account.account.tag'].search(osv.expression.OR(or_domains))

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
        return [(minus_tag_vals), (plus_tag_vals)]

    def _get_carryover_target_expression(self, options):
        self.ensure_one()

        if self.carryover_target:
            line_code, expr_label = self.carryover_target.split('.')
            return self.env['account.report.expression'].search([
                ('report_line_id.code', '=', line_code),
                ('label', '=', expr_label),
                ('report_line_id.report_id', '=', self.report_line_id.report_id.id),
            ])

        main_expr_label = re.sub("^_carryover_", '', self.label)
        target_label = '_applied_carryover_%s' % main_expr_label
        auto_chosen_target = self.report_line_id.expression_ids.filtered(lambda x: x.label == target_label)

        if not auto_chosen_target:
            raise UserError(_("Could not determine carryover target automatically for expression %s.", self.label))

        return auto_chosen_target

    def action_view_carryover_lines(self, options):
        date_from, date_to, dummy = self.report_line_id.report_id._get_date_bounds_info(options, self.date_scope)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Carryover lines for: %s', self.report_line_name),
            'res_model': 'account.report.external.value',
            'views': [(self.env.ref('account_reports.account_report_external_value_tree').id, 'list')],
            'domain': [
                ('target_report_expression_id', '=', self.id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ],
        }


class AccountReportColumn(models.Model):
    _name = "account.report.column"
    _description = "Accounting Report Column"
    _order = 'sequence, id'

    name = fields.Char(string="Name", translate=True, required=True)
    expression_label = fields.Char(string="Expression Label", required=True)
    sequence = fields.Integer(string="Sequence")
    report_id = fields.Many2one(string="Report", comodel_name='account.report')
    sortable = fields.Boolean(string="Sortable")
    figure_type = fields.Selection(string="Figure Type", selection=FIGURE_TYPE_SELECTION_VALUES, default="monetary", required=True)
    blank_if_zero = fields.Boolean(string="Blank if Zero", default=True, help="When checked, 0 values will not show in this column.")
    custom_audit_action_id = fields.Many2one(string="Custom Audit Action", comodel_name="ir.actions.act_window")


class AccountReportExternalValue(models.Model):
    _name = "account.report.external.value"
    _description = 'Accounting Report External Value'
    _check_company_auto = True
    _order = 'date, id'

    name = fields.Char(required=True)
    value = fields.Float(required=True)
    date = fields.Date(required=True)

    target_report_expression_id = fields.Many2one(string="Target Expression", comodel_name="account.report.expression", required=True)
    target_report_line_id = fields.Many2one(string="Target Line", related="target_report_expression_id.report_line_id")
    target_report_expression_label = fields.Char(string="Target Expression Label", related="target_report_expression_id.label")
    report_country_id = fields.Many2one(string="Country", related='target_report_line_id.report_id.country_id')

    company_id = fields.Many2one(string='Company', comodel_name='res.company', required=True, default=lambda self: self.env.company)

    foreign_vat_fiscal_position_id = fields.Many2one(
        string="Fiscal position",
        comodel_name='account.fiscal.position',
        domain="[('company_id', '=', company_id), ('country_id', '=', report_country_id), ('foreign_vat', '!=', False)]",
        check_company=True,
        help="The foreign fiscal position for which this external value is made.",
    )

    # Carryover fields
    carryover_origin_expression_label = fields.Char(string="Origin Expression Label")
    carryover_origin_report_line_id = fields.Many2one(string="Origin Line", comodel_name='account.report.line')

    @api.constrains('foreign_vat_fiscal_position_id', 'target_report_expression_id')
    def _check_fiscal_position(self):
        for record in self:
            if record.foreign_vat_fiscal_position_id and record.foreign_vat_fiscal_position_id.country_id != record.report_country_id:
                raise ValidationError(_("The country set on the foreign VAT fiscal position must match the one set on the report."))
