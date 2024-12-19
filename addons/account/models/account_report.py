# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import re
from collections import defaultdict

from odoo import models, fields, api, _, osv, Command
from odoo.exceptions import ValidationError, UserError

FIGURE_TYPE_SELECTION_VALUES = [
    ('monetary', "Monetary"),
    ('percentage', "Percentage"),
    ('integer', "Integer"),
    ('float', "Float"),
    ('date', "Date"),
    ('datetime', "Datetime"),
    ('boolean', 'Boolean'),
    ('string', 'String'),
]

DOMAIN_REGEX = re.compile(r'(-?sum)\((.*)\)')

class AccountReport(models.Model):
    _name = "account.report"
    _description = "Accounting Report"
    _order = 'sequence, id'

    #  CORE ==========================================================================================================================================

    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(string="Sequence")
    active = fields.Boolean(string="Active", default=True)
    line_ids = fields.One2many(string="Lines", comodel_name='account.report.line', inverse_name='report_id')
    column_ids = fields.One2many(string="Columns", comodel_name='account.report.column', inverse_name='report_id')
    root_report_id = fields.Many2one(string="Root Report", comodel_name='account.report', help="The report this report is a variant of.")
    variant_report_ids = fields.One2many(string="Variants", comodel_name='account.report', inverse_name='root_report_id')
    section_report_ids = fields.Many2many(string="Sections", comodel_name='account.report', relation="account_report_section_rel", column1="main_report_id", column2="sub_report_id")
    section_main_report_ids = fields.Many2many(string="Section Of", comodel_name='account.report', relation="account_report_section_rel", column1="sub_report_id", column2="main_report_id")
    use_sections = fields.Boolean(
        string="Composite Report",
        compute="_compute_use_sections", store=True, readonly=False,
        help="Create a structured report with multiple sections for convenient navigation and simultaneous printing.",
    )
    chart_template = fields.Selection(string="Chart of Accounts", selection=lambda self: self.env['account.chart.template']._select_chart_template())
    country_id = fields.Many2one(string="Country", comodel_name='res.country')
    only_tax_exigible = fields.Boolean(
        string="Only Tax Exigible Lines",
        compute=lambda x: x._compute_report_option_filter('only_tax_exigible'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    availability_condition = fields.Selection(
        string="Availability",
        selection=[('country', "Country Matches"), ('coa', "Chart of Accounts Matches"), ('always', "Always")],
        compute='_compute_default_availability_condition', readonly=False, store=True,
    )
    load_more_limit = fields.Integer(string="Load More Limit")
    search_bar = fields.Boolean(string="Search Bar")
    prefix_groups_threshold = fields.Integer(string="Prefix Groups Threshold")
    integer_rounding = fields.Selection(string="Integer Rounding", selection=[('HALF-UP', "Nearest"), ('UP', "Up"), ('DOWN', "Down")])

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
            ('this_tax_period', "This Tax Period"),
            ('last_tax_period', "Last Tax Period"),
        ],
        compute=lambda x: x._compute_report_option_filter('default_opening_date_filter', 'last_month'),
        readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )

    #  FILTERS =======================================================================================================================================
    # Those fields control the display of menus on the report

    filter_multi_company = fields.Selection(
        string="Multi-Company",
        selection=[('disabled', "Disabled"), ('selector', "Use Company Selector"), ('tax_units', "Use Tax Units")],
        compute=lambda x: x._compute_report_option_filter('filter_multi_company', 'disabled'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_date_range = fields.Boolean(
        string="Date Range",
        compute=lambda x: x._compute_report_option_filter('filter_date_range', True), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_show_draft = fields.Boolean(
        string="Draft Entries",
        compute=lambda x: x._compute_report_option_filter('filter_show_draft', True), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_unreconciled = fields.Boolean(
        string="Unreconciled Entries",
        compute=lambda x: x._compute_report_option_filter('filter_unreconciled', False), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_unfold_all = fields.Boolean(
        string="Unfold All",
        compute=lambda x: x._compute_report_option_filter('filter_unfold_all'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_hide_0_lines = fields.Selection(
        string="Hide lines at 0",
        selection=[('by_default', "Enabled by Default"), ('optional', "Optional"), ('never', "Never")],
        compute=lambda x: x._compute_report_option_filter('filter_hide_0_lines', 'optional'), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_period_comparison = fields.Boolean(
        string="Period Comparison",
        compute=lambda x: x._compute_report_option_filter('filter_period_comparison', True), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_growth_comparison = fields.Boolean(
        string="Growth Comparison",
        compute=lambda x: x._compute_report_option_filter('filter_growth_comparison', True), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_journals = fields.Boolean(
        string="Journals",
        compute=lambda x: x._compute_report_option_filter('filter_journals'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_analytic = fields.Boolean(
        string="Analytic Filter",
        compute=lambda x: x._compute_report_option_filter('filter_analytic'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_hierarchy = fields.Selection(
        string="Account Groups",
        selection=[('by_default', "Enabled by Default"), ('optional', "Optional"), ('never', "Never")],
        compute=lambda x: x._compute_report_option_filter('filter_hierarchy', 'optional'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_account_type = fields.Selection(
        string="Account Types",
        selection=[('both', "Payable and receivable"), ('payable', "Payable"), ('receivable', "Receivable"), ('disabled', 'Disabled')],
        compute=lambda x: x._compute_report_option_filter('filter_account_type', 'disabled'), readonly=False, store=True, depends=['root_report_id'],
    )
    filter_partner = fields.Boolean(
        string="Partners",
        compute=lambda x: x._compute_report_option_filter('filter_partner'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_fiscal_position = fields.Boolean(
        string="Filter Multivat",
        compute=lambda x: x._compute_report_option_filter('filter_fiscal_position'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )
    filter_aml_ir_filters = fields.Boolean(
        string="Favorite Filters", help="If activated, user-defined filters on journal items can be selected on this report",
        compute=lambda x: x._compute_report_option_filter('filter_aml_ir_filters'), readonly=False, store=True, depends=['root_report_id', 'section_main_report_ids'],
    )

    def _compute_report_option_filter(self, field_name, default_value=False):
        # We don't depend on the different filter fields on the root report, as we don't want a manual change on it to be reflected on all the reports
        # using it as their root (would create confusion). The root report filters are only used as some kind of default values.
        # When a report is a section, it can also get its default filter values from its parent composite report. This only happens when we're sure
        # the report is not used as a section of multiple reports, nor as a standalone report.
        for report in self.sorted(lambda x: not x.section_report_ids):
            # Reports are sorted in order to first treat the composite reports, in case they need to compute their filters a the same time
            # as their sections
            is_accessible = self.env['ir.actions.client'].search_count([('context', 'ilike', f"'report_id': {report.id}"), ('tag', '=', 'account_report')])
            is_variant = bool(report.root_report_id)
            if (is_accessible or is_variant) and report.section_main_report_ids:
                continue  # prevent updating the filters of a report when being added as a section of a report
            if report.root_report_id:
                report[field_name] = report.root_report_id[field_name]
            elif len(report.section_main_report_ids) == 1 and not is_accessible:
                report[field_name] = report.section_main_report_ids[field_name]
            else:
                report[field_name] = default_value

    @api.depends('root_report_id', 'country_id')
    def _compute_default_availability_condition(self):
        for report in self:
            if report.root_report_id and report.country_id:
                report.availability_condition = 'country'
            elif not report.availability_condition:
                report.availability_condition = 'always'

    @api.depends('section_report_ids')
    def _compute_use_sections(self):
        for report in self:
            report.use_sections = bool(report.section_report_ids)

    @api.constrains('root_report_id')
    def _validate_root_report_id(self):
        for report in self:
            if report.root_report_id.root_report_id:
                raise ValidationError(_("Only a report without a root report of its own can be selected as root report."))

    @api.constrains('line_ids')
    def _validate_parent_sequence(self):
        previous_lines = self.env['account.report.line']
        for line in self.line_ids:
            if line.parent_id and line.parent_id not in previous_lines:
                raise ValidationError(
                    _('Line "%s" defines line "%s" as its parent, but appears before it in the report. '
                      'The parent must always come first.', line.name, line.parent_id.name))
            previous_lines |= line

    @api.constrains('section_report_ids')
    def _validate_section_report_ids(self):
        for record in self:
            if any(section.section_report_ids for section in record.section_report_ids):
                raise ValidationError(_("The sections defined on a report cannot have sections themselves."))

    @api.constrains('availability_condition', 'country_id')
    def _validate_availability_condition(self):
        for record in self:
            if record.availability_condition == 'country' and not record.country_id:
                raise ValidationError(_("The Availability is set to 'Country Matches' but the field Country is not set."))

    @api.onchange('availability_condition')
    def _onchange_availability_condition(self):
        if self.availability_condition != 'country':
            self.country_id = None

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

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=report._get_copied_name()) for report, vals in zip(self, vals_list)]

    def copy(self, default=None):
        '''Copy the whole financial report hierarchy by duplicating each line recursively.

        :param default: Default values.
        :return: The copied account.report record.
        '''
        new_reports = super().copy(default=default)
        for old_report, new_report in zip(self, new_reports):
            code_mapping = {}
            for line in old_report.line_ids.filtered(lambda x: not x.parent_id):
                line._copy_hierarchy(new_report, code_mapping=code_mapping)

            # Replace line codes by their copy in aggregation formulas
            for expression in new_report.line_ids.expression_ids:
                if expression.engine == 'aggregation':
                    copied_formula = f" {expression.formula} "  # Add spaces so that the lookahead/lookbehind of the regex can work (we can't do a | in those)
                    for old_code, new_code in code_mapping.items():
                        copied_formula = re.sub(f"(?<=\\W){old_code}(?=\\W)", new_code, copied_formula)
                    expression.formula = copied_formula.strip()  # Remove the spaces introduced for lookahead/lookbehind

            old_report.column_ids.copy({'report_id': new_report.id})
        return new_reports

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
    def _compute_display_name(self):
        for report in self:
            if report.name:
                report.display_name = report.name + (f' ({report.country_id.code})' if report.country_id else '')
            else:
                report.display_name = False


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
    user_groupby = fields.Char(
        string="User Group By",
        compute='_compute_user_groupby', store=True, readonly=False, precompute=True,
        help="Comma-separated list of fields from account.move.line (Journal Item). When set, this line will generate sublines grouped by those keys.",
    )
    sequence = fields.Integer(string="Sequence")
    code = fields.Char(string="Code", help="Unique identifier for this line.")
    foldable = fields.Boolean(string="Foldable", help="By default, we always unfold the lines that can be. If this is checked, the line won't be unfolded by default, and a folding button will be displayed.")
    print_on_new_page = fields.Boolean('Print On New Page', help='When checked this line and everything after it will be printed on a new page.')
    action_id = fields.Many2one(string="Action", comodel_name='ir.actions.actions', help="Setting this field will turn the line into a link, executing the action when clicked.")
    hide_if_zero = fields.Boolean(string="Hide if Zero", help="This line and its children will be hidden when all of their columns are 0.")
    domain_formula = fields.Char(string="Domain Formula Shortcut", help="Internal field to shorten expression_ids creation for the domain engine", inverse='_inverse_domain_formula', store=False)
    account_codes_formula = fields.Char(string="Account Codes Formula Shortcut", help="Internal field to shorten expression_ids creation for the account_codes engine", inverse='_inverse_account_codes_formula', store=False)
    aggregation_formula = fields.Char(string="Aggregation Formula Shortcut", help="Internal field to shorten expression_ids creation for the aggregation engine", inverse='_inverse_aggregation_formula', store=False)
    external_formula = fields.Char(string="External Formula Shortcut", help="Internal field to shorten expression_ids creation for the external engine", inverse='_inverse_external_formula', store=False)
    horizontal_split_side = fields.Selection(string="Horizontal Split Side", selection=[('left', "Left"), ('right', "Right")], compute='_compute_horizontal_split_side', readonly=False, store=True, recursive=True)
    tax_tags_formula = fields.Char(string="Tax Tags Formula Shortcut", help="Internal field to shorten expression_ids creation for the tax_tags engine", inverse='_inverse_aggregation_tax_formula', store=False)

    _sql_constraints = [
        ('code_uniq', 'unique (report_id, code)', "A report line with the same code already exists."),
    ]

    @api.depends('parent_id.hierarchy_level')
    def _compute_hierarchy_level(self):
        for report_line in self:
            if report_line.parent_id:
                increase_level = 3 if report_line.parent_id.hierarchy_level == 0 else 2
                report_line.hierarchy_level = report_line.parent_id.hierarchy_level + increase_level
            else:
                report_line.hierarchy_level = 1

    @api.depends('parent_id.report_id')
    def _compute_report_id(self):
        for report_line in self:
            if report_line.parent_id:
                report_line.report_id = report_line.parent_id.report_id

    @api.depends('parent_id.horizontal_split_side')
    def _compute_horizontal_split_side(self):
        for report_line in self:
            if report_line.parent_id:
                report_line.horizontal_split_side = report_line.parent_id.horizontal_split_side

    @api.depends('groupby', 'expression_ids.engine')
    def _compute_user_groupby(self):
        for report_line in self:
            if not report_line.id and not report_line.user_groupby:
                report_line.user_groupby = report_line.groupby
            try:
                report_line._validate_groupby()
            except UserError:
                report_line.user_groupby = report_line.groupby

    @api.constrains('parent_id')
    def _validate_groupby_no_child(self):
        for report_line in self:
            if report_line.parent_id.groupby or report_line.parent_id.user_groupby:
                raise ValidationError(_("A line cannot have both children and a groupby value (line '%s').", report_line.parent_id.name))

    @api.constrains('groupby', 'user_groupby')
    def _validate_groupby(self):
        self.expression_ids._validate_engine()

    @api.constrains('parent_id')
    def _check_parent_line(self):
        for line in self.filtered(lambda x: x.parent_id == x):
            raise ValidationError(_('Line "%s" defines itself as its parent.', line.name))

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
            'code': self._get_copied_code(),
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
            expression.copy(copy_defaults)

    def _get_copied_code(self):
        '''Look for an unique copied code.

        :return: an unique code for the copied account.report.line
        '''
        self.ensure_one()
        if not self.code:
            return False
        code = self.code + '_COPY'
        while self.search_count([('code', '=', code)]) > 0:
            code += '_COPY'
        return code

    def _inverse_domain_formula(self):
        self._create_report_expression(engine='domain')

    def _inverse_aggregation_formula(self):
        self._create_report_expression(engine='aggregation')

    def _inverse_aggregation_tax_formula(self):
        self._create_report_expression(engine='tax_tags')

    def _inverse_account_codes_formula(self):
        self._create_report_expression(engine='account_codes')

    def _inverse_external_formula(self):
        self._create_report_expression(engine='external')

    def _create_report_expression(self, engine):
        # create account.report.expression for each report line based on the formula provided to each
        # engine-related field. This makes xmls a bit shorter
        vals_list = []
        xml_ids = self.expression_ids.filtered(lambda exp: exp.label == 'balance').get_external_id()
        for report_line in self:
            if engine == 'domain' and report_line.domain_formula:
                subformula, formula = DOMAIN_REGEX.match(report_line.domain_formula or '').groups()
                # Resolve the calls to ref(), to mimic the fact those formulas are normally given with an eval="..." in XML
                formula = re.sub(r'''\bref\((?P<quote>['"])(?P<xmlid>.+?)(?P=quote)\)''', lambda m: str(self.env.ref(m['xmlid']).id), formula)
            elif engine == 'account_codes' and report_line.account_codes_formula:
                subformula, formula = None, report_line.account_codes_formula
            elif engine == 'aggregation' and report_line.aggregation_formula:
                subformula, formula = None, report_line.aggregation_formula
            elif engine == 'external' and report_line.external_formula:
                subformula, formula = 'editable', 'most_recent'
                if report_line.external_formula == 'percentage':
                    subformula = 'editable;rounding=0'
                elif report_line.external_formula == 'monetary':
                    formula = 'sum'
            elif engine == 'tax_tags' and report_line.tax_tags_formula:
                subformula, formula = None, report_line.tax_tags_formula
            else:
                # If we want to replace a formula shortcut with a full-syntax expression, we need to make the formula field falsy
                # We can't simply remove it from the xml because it won't be updated
                # If the formula field is falsy, we need to remove the expression that it generated
                report_line.expression_ids.filtered(lambda exp: exp.engine == engine and exp.label == 'balance' and not xml_ids.get(exp.id)).unlink()
                continue

            vals = {
                'report_line_id': report_line.id,
                'label': 'balance',
                'engine': engine,
                'formula': formula.lstrip(' \t\n'),  # Avoid IndentationError in evals
                'subformula': subformula
            }
            if engine == 'external' and report_line.external_formula:
                vals['figure_type'] = report_line.external_formula

            if report_line.expression_ids:
                # expressions already exists, update the first expression with the right engine
                # since syntactic sugar aren't meant to be used with multiple expressions
                for expression in report_line.expression_ids:
                    if expression.label == 'balance':
                        # If we had a 'balance' expression coming from the xml and are using a formula shortcut on top of it,
                        # we expect the shortcut to replace the original expression. The full declaration should also
                        # be removed from the data file, leading to the ORM deleting it automatically.
                        if xml_ids.get(expression.id):
                            expression.unlink()
                            vals_list.append(vals)
                        else:
                            expression.write(vals)
                        break
            else:
                # else prepare batch creation
                vals_list.append(vals)

        if vals_list:
            self.env['account.report.expression'].create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_child_expressions(self):
        """
        We explicitly unlink child expressions.
        This is necessary even if there is an ondelete='cascade' on it, because
        the @api.ondelete method _unlink_archive_used_tags is not automatically
        called if the parent model is deleted.
        """
        self.expression_ids.unlink()


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
             "(on a _carryover_*-labeled expression), in case it is different from the parent line."
    )

    _sql_constraints = [
        (
            "domain_engine_subformula_required",
            "CHECK(engine != 'domain' OR subformula IS NOT NULL)",
            "Expressions using 'domain' engine should all have a subformula."
        ),
        (
            "line_label_uniq",
            "UNIQUE(report_line_id,label)",
            "The expression label must be unique per report line."
        ),
    ]

    @api.constrains('carryover_target', 'label')
    def _check_carryover_target(self):
        for expression in self:
            if expression.carryover_target and not expression.label.startswith('_carryover_'):
                raise UserError(_("You cannot use the field carryover_target in an expression that does not have the label starting with _carryover_"))
            elif expression.carryover_target and not expression.carryover_target.split('.')[1].startswith('_applied_carryover_'):
                raise UserError(_("When targeting an expression for carryover, the label of that expression must start with _applied_carryover_"))

    @api.constrains('formula')
    def _check_domain_formula(self):
        for expression in self.filtered(lambda expr: expr.engine == 'domain'):
            try:
                domain = ast.literal_eval(expression.formula)
                self.env['account.move.line']._where_calc(domain)
            except:
                raise UserError(_("Invalid domain for expression '%s' of line '%s': %s",
                                expression.label, expression.report_line_name, expression.formula))

    @api.depends('engine')
    def _compute_auditable(self):
        auditable_engines = self._get_auditable_engines()
        for expression in self:
            expression.auditable = expression.engine in auditable_engines

    @api.constrains('engine', 'report_line_id')
    def _validate_engine(self):
        for expression in self:
            if expression.engine == 'aggregation' and (expression.report_line_id.groupby or expression.report_line_id.user_groupby):
                raise ValidationError(_(
                    "Groupby feature isn't supported by aggregation engine. Please remove the groupby value on '%s'",
                    expression.report_line_id.display_name,
                ))

    def _get_auditable_engines(self):
        return {'tax_tags', 'domain', 'account_codes', 'external', 'aggregation'}

    def _strip_formula(self, vals):
        if 'formula' in vals and isinstance(vals['formula'], str):
            vals['formula'] = re.sub(r'\s+', ' ', vals['formula'].strip())

    def _create_tax_tags(self, tag_name, country):
        existing_tags = self.env['account.account.tag']._get_tax_tags(tag_name, country.id)
        if len(existing_tags) < 2:
            # We can have only one tag in case we archived it and deleted its unused complement sign
            tag_vals = self._get_tags_create_vals(tag_name, country.id, existing_tag=existing_tags)
            self.env['account.account.tag'].create(tag_vals)

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
                self._create_tax_tags(tag_name, country)

        return result

    def write(self, vals):

        self._strip_formula(vals)

        if vals.get('engine') == 'tax_tags':
            tag_name = vals.get('formula') or self.formula
            country = self.report_line_id.report_id.country_id
            self._create_tax_tags(tag_name, country)
            return super().write(vals)

        # In case the engine is changed we don't propagate any change to the tags themselves
        if 'formula' not in vals or (vals.get('engine') and vals['engine'] != 'tax_tags'):
            return super().write(vals)

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
                        if self.pool['account.tax'].name.translate:
                            positive_tags._update_field_translations('name', {'en_US': f"+{vals['formula']}"})
                            negative_tags._update_field_translations('name', {'en_US': f"-{vals['formula']}"})
                        else:
                            positive_tags.name = f"+{vals['formula']}"
                            negative_tags.name = f"-{vals['formula']}"
                    else:
                        # Else, create a new tag. Its the compute functions will make sure it is properly linked to the expressions
                        tag_vals = self.env['account.report.expression']._get_tags_create_vals(vals['formula'], country.id)
                        self.env['account.account.tag'].create(tag_vals)

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_archive_used_tags(self):
        """
        Manages unlink or archive of tax_tags when account.report.expression are deleted.
        If a tag is still in use on amls, we archive it.
        """
        expressions_tags = self._get_matching_tags()
        tags_to_archive = self.env['account.account.tag']
        tags_to_unlink = self.env['account.account.tag']
        for tag in expressions_tags:
            other_expression_using_tag = self.env['account.report.expression'].sudo().search([
                ('engine', '=', 'tax_tags'),
                ('formula', '=', tag.with_context(lang='en_US').name[1:]),  # we escape the +/- sign
                ('report_line_id.report_id.country_id', '=', tag.country_id.id),
                ('id', 'not in', self.ids),
            ], limit=1)
            if not other_expression_using_tag:
                aml_using_tag = self.env['account.move.line'].sudo().search([('tax_tag_ids', 'in', tag.id)], limit=1)
                if aml_using_tag:
                    tags_to_archive += tag
                else:
                    tags_to_unlink += tag

        if tags_to_archive or tags_to_unlink:
            rep_lines_with_tag = self.env['account.tax.repartition.line'].sudo().search([('tag_ids', 'in', (tags_to_archive + tags_to_unlink).ids)])
            rep_lines_with_tag.write({'tag_ids': [Command.unlink(tag.id) for tag in tags_to_archive + tags_to_unlink]})
            tags_to_archive.active = False
            tags_to_unlink.unlink()

    @api.depends('report_line_name', 'label')
    def _compute_display_name(self):
        for expr in self:
            expr.display_name = f'{expr.report_line_name} [{expr.label}]'


    def _expand_aggregations(self):
        """Return self and its full aggregation expression dependency"""
        result = self

        to_expand = self.filtered(lambda x: x.engine == 'aggregation')
        while to_expand:
            domains = []
            sub_expressions = self.env['account.report.expression']

            for candidate_expr in to_expand:
                if candidate_expr.formula == 'sum_children':
                    sub_expressions |= candidate_expr.report_line_id.children_ids.expression_ids.filtered(lambda e: e.label == candidate_expr.label)
                else:
                    labels_by_code = candidate_expr._get_aggregation_terms_details()

                    cross_report_domain = []
                    if candidate_expr.subformula != 'cross_report':
                        cross_report_domain = [('report_line_id.report_id', '=', candidate_expr.report_line_id.report_id.id)]

                    for line_code, expr_labels in labels_by_code.items():
                        dependency_domain = [('report_line_id.code', '=', line_code), ('label', 'in', tuple(expr_labels))] + cross_report_domain
                        domains.append(dependency_domain)

            if domains:
                sub_expressions |= self.env['account.report.expression'].search(osv.expression.OR(domains))

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

            if expression.subformula:
                if_other_expr_match = re.match(r'if_other_expr_(above|below)\((?P<line_code>.+)[.](?P<expr_label>.+),.+\)', expression.subformula)
                if if_other_expr_match:
                    totals_by_code[if_other_expr_match['line_code']].add(if_other_expr_match['expr_label'])

        return totals_by_code

    def _get_matching_tags(self, sign=None):
        """ Returns all the signed account.account.tags records whose name matches any of the formulas of the tax_tags expressions contained in self.
        """
        tag_expressions = self.filtered(lambda x: x.engine == 'tax_tags')
        if not tag_expressions:
            return self.env['account.account.tag']

        or_domains = []
        for tag_expression in tag_expressions:
            country = tag_expression.report_line_id.report_id.country_id
            or_domains.append(self.env['account.account.tag']._get_tax_tags_domain(tag_expression.formula, country.id, sign))

        return self.env['account.account.tag'].with_context(active_test=False, lang='en_US').search(osv.expression.OR(or_domains))

    @api.model
    def _get_tags_create_vals(self, tag_name, country_id, existing_tag=None):
        """
        We create the plus and minus tags with tag_name.
        In case there is an existing_tag (which can happen if we deleted its unused complement sign)
        we only recreate the missing sign.
        """
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
        res = []
        if not existing_tag or not existing_tag.tax_negate:
            res.append(minus_tag_vals)
        if not existing_tag or existing_tag.tax_negate:
            res.append(plus_tag_vals)
        return res

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
    blank_if_zero = fields.Boolean(string="Blank if Zero", help="When checked, 0 values will not show in this column.")
    custom_audit_action_id = fields.Many2one(string="Custom Audit Action", comodel_name="ir.actions.act_window")


class AccountReportExternalValue(models.Model):
    _name = "account.report.external.value"
    _description = 'Accounting Report External Value'
    _check_company_auto = True
    _order = 'date, id'

    name = fields.Char(required=True)
    value = fields.Float(string="Numeric Value")
    text_value = fields.Char(string="Text Value")
    date = fields.Date(required=True)

    target_report_expression_id = fields.Many2one(string="Target Expression", comodel_name="account.report.expression", required=True, ondelete="cascade")
    target_report_line_id = fields.Many2one(string="Target Line", related="target_report_expression_id.report_line_id")
    target_report_expression_label = fields.Char(string="Target Expression Label", related="target_report_expression_id.label")
    report_country_id = fields.Many2one(string="Country", related='target_report_line_id.report_id.country_id')

    company_id = fields.Many2one(string='Company', comodel_name='res.company', required=True, default=lambda self: self.env.company)

    foreign_vat_fiscal_position_id = fields.Many2one(
        string="Fiscal position",
        comodel_name='account.fiscal.position',
        domain="[('country_id', '=', report_country_id), ('foreign_vat', '!=', False)]",
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
