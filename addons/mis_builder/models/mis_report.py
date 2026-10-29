# Copyright 2014 ACSONE SA/NV (<http://acsone.eu>)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime
import logging
import re
import time
from collections import defaultdict

import dateutil
import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.models import expression as osv_expression
from odoo.tools.safe_eval import (
    datetime as safe_datetime,
)
from odoo.tools.safe_eval import (
    dateutil as safe_dateutil,
)
from odoo.tools.safe_eval import (
    safe_eval,
)
from odoo.tools.safe_eval import (
    time as safe_time,
)

from .accounting_none import AccountingNone
from .aep import AccountingExpressionProcessor as AEP
from .aggregate import _avg, _max, _min, _sum
from .expression_evaluator import ExpressionEvaluator
from .kpimatrix import KpiMatrix
from .mis_kpi_data import ACC_AVG, ACC_NONE, ACC_SUM
from .mis_report_style import CMP_DIFF, CMP_NONE, CMP_PCT, TYPE_NUM, TYPE_PCT, TYPE_STR
from .mis_safe_eval import DataError
from .simple_array import SimpleArray, named_simple_array

_logger = logging.getLogger(__name__)


class SubKPITupleLengthError(UserError):
    pass


class SubKPIUnknownTypeError(UserError):
    pass


class AutoStruct:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _utc_midnight(d, tz_name, add_day=0):
    d = fields.Datetime.from_string(d) + datetime.timedelta(days=add_day)
    utc_tz = pytz.timezone("UTC")
    context_tz = pytz.timezone(tz_name)
    local_timestamp = context_tz.localize(d, is_dst=False)
    return fields.Datetime.to_string(local_timestamp.astimezone(utc_tz))


def _python_var(var_str):
    return re.sub(r"\W|^(?=\d)", "_", var_str).lower()


def _is_valid_python_var(name):
    return re.match("[_A-Za-z][_a-zA-Z0-9]*$", name)


class MisReportKpi(models.Model):
    """A KPI is an element (ie a line) of a MIS report.

    In addition to a name and description, it has an expression
    to compute it based on queries defined in the MIS report.
    It also has various informations defining how to render it
    (numeric or percentage or a string, a prefix, a suffix, divider) and
    how to render comparison of two values of the KPI.
    KPI's have a sequence and are ordered inside the MIS report.
    """

    _name = "mis.report.kpi"
    _description = "MIS Report KPI"

    name = fields.Char(required=True)
    description = fields.Char(required=True, translate=True)
    multi = fields.Boolean()
    expression = fields.Char(
        compute="_compute_expression",
        inverse="_inverse_expression",
    )
    expression_ids = fields.One2many(
        comodel_name="mis.report.kpi.expression",
        inverse_name="kpi_id",
        copy=True,
        string="Expressions",
    )
    auto_expand_accounts = fields.Boolean(string="Display details by account")
    auto_expand_accounts_style_id = fields.Many2one(
        string="Style for account detail rows",
        comodel_name="mis.report.style",
        required=False,
    )
    style_id = fields.Many2one(
        string="Style", comodel_name="mis.report.style", required=False
    )
    style_expression = fields.Char(
        help="An expression that returns a style depending on the KPI value. "
        "Such style is applied on top of the row style.",
    )
    type = fields.Selection(
        [
            (TYPE_NUM, _("Numeric")),
            (TYPE_PCT, _("Percentage")),
            (TYPE_STR, _("String")),
        ],
        required=True,
        string="Value type",
        default=TYPE_NUM,
    )
    compare_method = fields.Selection(
        [
            (CMP_DIFF, _("Difference")),
            (CMP_PCT, _("Percentage")),
            (CMP_NONE, _("None")),
        ],
        required=True,
        string="Comparison Method",
        default=CMP_PCT,
    )
    accumulation_method = fields.Selection(
        [(ACC_SUM, _("Sum")), (ACC_AVG, _("Average")), (ACC_NONE, _("None"))],
        required=True,
        default=ACC_SUM,
        help="Determines how values of this kpi spanning over a "
        "time period are transformed to match the reporting period. "
        "Sum: values of shorter period are added, "
        "values of longest or partially overlapping periods are "
        "adjusted pro-rata temporis.\n"
        "Average: values of included period are averaged "
        "with a pro-rata temporis weight.",
    )
    sequence = fields.Integer(default=100)
    report_id = fields.Many2one("mis.report", required=True, ondelete="cascade")

    _order = "sequence, id"

    def name_get(self):
        res = []
        for rec in self:
            name = f"{rec.description} ({rec.name})"
            res.append((rec.id, name))
        return res

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        domain = args or []
        domain += ["|", ("name", operator, name), ("description", operator, name)]
        return self.search(domain, limit=limit).name_get()

    @api.constrains("name")
    def _check_name(self):
        for record in self:
            if not _is_valid_python_var(record.name):
                raise ValidationError(
                    _("KPI name ({}) must be a valid python identifier").format(
                        record.name
                    )
                )

    @api.depends("expression_ids.subkpi_id.name", "expression_ids.name")
    def _compute_expression(self):
        for kpi in self:
            exprs = []
            for expression in kpi.expression_ids:
                if expression.subkpi_id:
                    exprs.append(
                        f"{expression.subkpi_id.name}\xa0=\xa0{expression.name}"
                    )
                else:
                    exprs.append(expression.name or "AccountingNone")
            kpi.expression = ",\n".join(exprs)

    def _inverse_expression(self):
        for kpi in self:
            if kpi.multi:
                continue
            if kpi.expression_ids:
                kpi.expression_ids[0].write({"name": kpi.expression, "subkpi_id": None})
                for expression in kpi.expression_ids[1:]:
                    expression.unlink()
            else:
                expression = self.env["mis.report.kpi.expression"].new(
                    {"name": kpi.expression}
                )
                kpi.expression_ids += expression

    @api.onchange("multi")
    def _onchange_multi(self):
        for kpi in self:
            if not kpi.multi:
                if kpi.expression_ids:
                    kpi.expression = kpi.expression_ids[0].name
                else:
                    kpi.expression = None
            else:
                expressions = []
                for subkpi in kpi.report_id.subkpi_ids:
                    expressions.append(
                        (0, 0, {"name": kpi.expression, "subkpi_id": subkpi.id})
                    )
                kpi.expression_ids = expressions

    @api.onchange("description")
    def _onchange_description(self):
        """construct name from description"""
        if self.description and not self.name:
            self.name = _python_var(self.description)

    @api.onchange("type")
    def _onchange_type(self):
        if self.type == TYPE_NUM:
            self.compare_method = CMP_PCT
            self.accumulation_method = ACC_SUM
        elif self.type == TYPE_PCT:
            self.compare_method = CMP_DIFF
            self.accumulation_method = ACC_AVG
        elif self.type == TYPE_STR:
            self.compare_method = CMP_NONE
            self.accumulation_method = ACC_NONE

    def _get_expression_str_for_subkpi(self, subkpi):
        e = self._get_expression_for_subkpi(subkpi)
        return e and e.name or ""

    def _get_expression_for_subkpi(self, subkpi):
        for expression in self.expression_ids:
            if expression.subkpi_id == subkpi:
                return expression
        return None

    def _get_expressions(self, subkpis):
        if subkpis and self.multi:
            return [self._get_expression_for_subkpi(subkpi) for subkpi in subkpis]
        else:
            if self.expression_ids:
                assert len(self.expression_ids) == 1
                assert not self.expression_ids[0].subkpi_id
                return self.expression_ids
            else:
                return [None]


class MisReportSubkpi(models.Model):
    _name = "mis.report.subkpi"
    _description = "MIS Report Sub-KPI"
    _order = "sequence, id"

    sequence = fields.Integer(default=1)
    report_id = fields.Many2one(
        comodel_name="mis.report", required=True, ondelete="cascade"
    )
    name = fields.Char(required=True)
    description = fields.Char(required=True, translate=True)
    expression_ids = fields.One2many("mis.report.kpi.expression", "subkpi_id")

    @api.constrains("name")
    def _check_name(self):
        for record in self:
            if not _is_valid_python_var(record.name):
                raise ValidationError(
                    _("Sub-KPI name ({}) must be a valid python identifier").format(
                        record.name
                    )
                )

    @api.onchange("description")
    def _onchange_description(self):
        """construct name from description"""
        if self.description and not self.name:
            self.name = _python_var(self.description)


class MisReportKpiExpression(models.Model):
    """A KPI Expression is an expression of a line of a MIS report Kpi.
    It's used to compute the kpi value.
    """

    _name = "mis.report.kpi.expression"
    _description = "MIS Report KPI Expression"
    _order = "sequence, name, id"

    sequence = fields.Integer(related="subkpi_id.sequence", store=True, readonly=True)
    name = fields.Char(string="Expression")
    kpi_id = fields.Many2one("mis.report.kpi", required=True, ondelete="cascade")
    # TODO FIXME set readonly=True when onchange('subkpi_ids') below works
    subkpi_id = fields.Many2one("mis.report.subkpi", readonly=False, ondelete="cascade")

    _sql_constraints = [
        (
            "subkpi_kpi_unique",
            "unique(subkpi_id, kpi_id)",
            "Sub KPI must be used once and only once for each KPI",
        )
    ]

    def name_get(self):
        res = []
        for rec in self:
            kpi = rec.kpi_id
            subkpi = rec.subkpi_id
            if subkpi:
                name = "{} / {} ({}.{})".format(
                    kpi.description, subkpi.description, kpi.name, subkpi.name
                )
            else:
                name = rec.kpi_id.display_name
            res.append((rec.id, name))
        return res

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        # TODO maybe implement negative search operators, although
        #      there is not really a use case for that
        domain = args or []
        splitted_name = name.split(".", 2)
        name_search_domain = []
        if "." in name:
            kpi_name, subkpi_name = splitted_name[0], splitted_name[1]
            name_search_domain = osv_expression.AND(
                [
                    name_search_domain,
                    [
                        "|",
                        "|",
                        "&",
                        ("kpi_id.name", "=", kpi_name),
                        ("subkpi_id.name", operator, subkpi_name),
                        ("kpi_id.description", operator, name),
                        ("subkpi_id.description", operator, name),
                    ],
                ]
            )
        name_search_domain = osv_expression.OR(
            [
                name_search_domain,
                [
                    "|",
                    ("kpi_id.name", operator, name),
                    ("kpi_id.description", operator, name),
                ],
            ]
        )
        domain = osv_expression.AND([domain, name_search_domain])
        return self.search(domain, limit=limit).name_get()


class MisReportQuery(models.Model):
    """A query to fetch arbitrary data for a MIS report.

    A query works on a model and has a domain and list of fields to fetch.
    At runtime, the domain is expanded with a "and" on the date/datetime field.
    """

    _name = "mis.report.query"
    _description = "MIS Report Query"

    @api.depends("field_ids")
    def _compute_field_names(self):
        for record in self:
            field_names = [field.name for field in record.field_ids]
            record.field_names = ", ".join(field_names)

    name = fields.Char(required=True)
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade")
    field_ids = fields.Many2many(
        "ir.model.fields", required=True, string="Fields to fetch"
    )
    field_names = fields.Char(
        compute="_compute_field_names", string="Fetched fields name"
    )
    aggregate = fields.Selection(
        [
            ("sum", _("Sum")),
            ("avg", _("Average")),
            ("min", _("Min")),
            ("max", _("Max")),
        ],
    )
    date_field = fields.Many2one(
        comodel_name="ir.model.fields",
        required=True,
        domain=[("ttype", "in", ("date", "datetime"))],
        ondelete="cascade",
    )
    domain = fields.Char()
    report_id = fields.Many2one(
        comodel_name="mis.report", required=True, ondelete="cascade"
    )

    _order = "name"

    @api.constrains("name")
    def _check_name(self):
        for record in self:
            if not _is_valid_python_var(record.name):
                raise ValidationError(
                    _("Query name ({}) must be valid python identifier").format(
                        record.name
                    )
                )


class MisReport(models.Model):
    """A MIS report template (without period information)

    The MIS report holds:
    * a list of explicit queries; the result of each query is
      stored in a variable with same name as a query, containing as list
      of data structures populated with attributes for each fields to fetch;
      when queries have an aggregate method and no fields to group, it returns
      a data structure with the aggregated fields
    * a list of KPI to be evaluated based on the variables resulting
      from the accounting data and queries (KPI expressions can references
      queries and accounting expression - see AccoutingExpressionProcessor)
    """

    _name = "mis.report"
    _description = "MIS Report Template"

    def _default_move_lines_source(self):
        return self.env["ir.model"].sudo().search([("model", "=", "account.move.line")])

    name = fields.Char(required=True, translate=True)
    description = fields.Char(required=False, translate=True)
    style_id = fields.Many2one(string="Style", comodel_name="mis.report.style")
    query_ids = fields.One2many(
        "mis.report.query", "report_id", string="Queries", copy=True
    )
    kpi_ids = fields.One2many("mis.report.kpi", "report_id", string="KPI's", copy=True)
    subkpi_ids = fields.One2many(
        "mis.report.subkpi", "report_id", string="Sub KPI", copy=True
    )
    subreport_ids = fields.One2many(
        "mis.report.subreport", "report_id", string="Sub reports", copy=True
    )
    all_kpi_ids = fields.One2many(
        comodel_name="mis.report.kpi",
        compute="_compute_all_kpi_ids",
        help="KPIs of this report and subreports.",
    )
    move_lines_source = fields.Many2one(
        comodel_name="ir.model",
        domain=[
            ("field_id.name", "=", "debit"),
            ("field_id.name", "=", "credit"),
            ("field_id.name", "=", "account_id"),
            ("field_id.name", "=", "date"),
            ("field_id.name", "=", "company_id"),
        ],
        default=_default_move_lines_source,
        required=True,
        ondelete="cascade",
        help="A 'move line like' model, ie having at least debit, credit, "
        "date, account_id and company_id fields. This model is the "
        "data source for column Actuals.",
    )
    account_model = fields.Char(compute="_compute_account_model")

    @api.depends("kpi_ids", "subreport_ids")
    def _compute_all_kpi_ids(self):
        for rec in self:
            rec.all_kpi_ids = rec.kpi_ids | rec.subreport_ids.mapped(
                "subreport_id.kpi_ids"
            )

    @api.depends("move_lines_source")
    def _compute_account_model(self):
        for record in self:
            record.account_model = (
                record.move_lines_source.sudo()
                .field_id.filtered(lambda r: r.name == "account_id")
                .relation
            )

    @api.onchange("subkpi_ids")
    def _on_change_subkpi_ids(self):
        """Update kpi expressions when subkpis change on the report,
        so the list of kpi expressions is always up-to-date"""
        for kpi in self.kpi_ids:
            if not kpi.multi:
                continue
            new_subkpis = {subkpi for subkpi in self.subkpi_ids}
            expressions = []
            for expression in kpi.expression_ids:
                assert expression.subkpi_id  # must be true if kpi is multi
                if expression.subkpi_id not in self.subkpi_ids:
                    expressions.append((2, expression.id, None))  # remove
                else:
                    new_subkpis.remove(expression.subkpi_id)  # no change
            for subkpi in new_subkpis:
                # TODO FIXME this does not work, while the remove above works
                expressions.append(
                    (0, None, {"name": False, "subkpi_id": subkpi.id})
                )  # add empty expressions for new subkpis
            if expressions:
                kpi.expression_ids = expressions

    def get_wizard_report_action(self):
        xmlid = "mis_builder.mis_report_instance_view_action"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        view = self.env.ref("mis_builder.wizard_mis_report_instance_view_form")
        action.update(
            {
                "view_id": view.id,
                "views": [(view.id, "form")],
                "target": "new",
                "context": {
                    "default_report_id": self.id,
                    "default_name": self.name,
                    "default_temporary": True,
                },
            }
        )
        return action

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or [])
        default["name"] = _("%s (copy)") % self.name
        new = super().copy(default)
        # after a copy, we have new subkpis, but the expressions
        # subkpi_id fields still point to the original one, so
        # we patch them after copying
        subkpis_by_name = {sk.name: sk for sk in new.subkpi_ids}
        for subkpi in self.subkpi_ids:
            # search expressions linked to subkpis of the original report
            exprs = self.env["mis.report.kpi.expression"].search(
                [("kpi_id.report_id", "=", new.id), ("subkpi_id", "=", subkpi.id)]
            )
            # and replace them with references to subkpis of the new report
            exprs.write({"subkpi_id": subkpis_by_name[subkpi.name].id})
        return new

    # TODO: kpi name cannot be start with query name

    def prepare_kpi_matrix(self, multi_company=False):
        self.ensure_one()
        kpi_matrix = KpiMatrix(self.env, multi_company, self.account_model)
        for kpi in self.kpi_ids:
            kpi_matrix.declare_kpi(kpi)
        return kpi_matrix

    def _prepare_aep(self, companies, currency=None):
        self.ensure_one()
        aep = AEP(companies, currency, self.account_model)
        for kpi in self.all_kpi_ids:
            for expression in kpi.expression_ids:
                if expression.name:
                    aep.parse_expr(expression.name)
        aep.done_parsing()
        return aep

    def prepare_locals_dict(self):
        return {
            "sum": _sum,
            "min": _min,
            "max": _max,
            "len": len,
            "avg": _avg,
            "time": time,
            "datetime": datetime,
            "dateutil": dateutil,
            "AccountingNone": AccountingNone,
            "SimpleArray": SimpleArray,
        }

    def _fetch_queries(self, date_from, date_to, get_additional_query_filter=None):
        self.ensure_one()
        res = {}
        for query in self.query_ids:
            query_sudo = query.sudo()
            model = self.env[query_sudo.model_id.model]
            eval_context = {
                "env": self.env,
                "time": safe_time,
                "datetime": safe_datetime,
                "dateutil": safe_dateutil,
                # deprecated
                "uid": self.env.uid,
                "context": self.env.context,
            }
            domain = query.domain and safe_eval(query.domain, eval_context) or []
            if get_additional_query_filter:
                domain.extend(get_additional_query_filter(query))
            if query_sudo.date_field.ttype == "date":
                domain.extend(
                    [
                        (query_sudo.date_field.name, ">=", date_from),
                        (query_sudo.date_field.name, "<=", date_to),
                    ]
                )
            else:
                tz = str(self.env["ir.fields.converter"]._input_tz())
                datetime_from = _utc_midnight(date_from, tz)
                datetime_to = _utc_midnight(date_to, tz, add_day=1)
                domain.extend(
                    [
                        (query_sudo.date_field.name, ">=", datetime_from),
                        (query_sudo.date_field.name, "<", datetime_to),
                    ]
                )
            field_names = [f.name for f in query_sudo.field_ids]
            all_stored = all([model._fields[f].store for f in field_names])
            if not query.aggregate:
                data = model.search_read(domain, field_names)
                res[query.name] = [AutoStruct(**d) for d in data]
            elif query.aggregate == "sum" and all_stored:
                # use read_group to sum stored fields
                data = model.read_group(domain, field_names, [])
                s = AutoStruct(count=data[0]["__count"])
                for field_name in field_names:
                    try:
                        v = data[0][field_name]
                    except KeyError:
                        _logger.error(
                            "field %s not found in read_group " "for %s; not summable?",
                            field_name,
                            model._name,
                        )
                        v = AccountingNone
                    setattr(s, field_name, v)
                res[query.name] = s
            else:
                data = model.search_read(domain, field_names)
                s = AutoStruct(count=len(data))
                if query.aggregate == "min":
                    agg = _min
                elif query.aggregate == "max":
                    agg = _max
                elif query.aggregate == "avg":
                    agg = _avg
                elif query.aggregate == "sum":
                    agg = _sum
                for field_name in field_names:
                    setattr(s, field_name, agg([d[field_name] for d in data]))
                res[query.name] = s
        return res

    def _declare_and_compute_col(  # noqa: C901 (TODO simplify this fnction)
        self,
        expression_evaluator,
        kpi_matrix,
        col_key,
        col_label,
        col_description,
        subkpis_filter,
        locals_dict,
        no_auto_expand_accounts=False,
    ):
        """This is the main computation loop.

        It evaluates the kpis and puts the results in the KpiMatrix.
        Evaluation is done through the expression_evaluator so data sources
        can provide their own mean of obtaining the data (eg preset
        kpi values for budget, or alternative move line sources).
        """

        if subkpis_filter:
            # TODO filter by subkpi names
            subkpis = [subkpi for subkpi in self.subkpi_ids if subkpi in subkpis_filter]
        else:
            subkpis = self.subkpi_ids

        SimpleArray_cls = named_simple_array(
            f"SimpleArray_{col_key}", [subkpi.name for subkpi in subkpis]
        )
        locals_dict["SimpleArray"] = SimpleArray_cls

        col = kpi_matrix.declare_col(
            col_key, col_label, col_description, locals_dict, subkpis
        )

        compute_queue = self.kpi_ids
        recompute_queue = []
        while True:
            for kpi in compute_queue:
                # build the list of expressions for this kpi
                expressions = kpi._get_expressions(subkpis)

                (
                    vals,
                    drilldown_args,
                    name_error,
                ) = expression_evaluator.eval_expressions(expressions, locals_dict)
                for drilldown_arg in drilldown_args:
                    if not drilldown_arg:
                        continue
                    drilldown_arg["period_id"] = col_key
                    drilldown_arg["kpi_id"] = kpi.id

                if name_error:
                    recompute_queue.append(kpi)
                else:
                    # no error, set it in locals_dict so it can be used
                    # in computing other kpis
                    if not subkpis or not kpi.multi:
                        locals_dict[kpi.name] = vals[0]
                    else:
                        locals_dict[kpi.name] = SimpleArray_cls(vals)

                # even in case of name error we set the result in the matrix
                # so the name error will be displayed if it cannot be
                # resolved by recomputing later

                if subkpis and not kpi.multi:
                    # here we have one expression for this kpi, but
                    # multiple subkpis (so this kpi is most probably
                    # a sum or other operation on multi-valued kpis)
                    if isinstance(vals[0], tuple):
                        vals = vals[0]
                        if len(vals) != col.colspan:
                            raise SubKPITupleLengthError(
                                _(
                                    'KPI "%(kpi)s" is valued as a tuple of '
                                    "length %(length)s while a tuple of length"
                                    "%(expected_length)s is expected.",
                                    kpi=kpi.description,
                                    length=len(vals),
                                    expected_length=col.colspan,
                                )
                            )
                    elif isinstance(vals[0], DataError):
                        vals = (vals[0],) * col.colspan
                    else:
                        raise SubKPIUnknownTypeError(
                            _(
                                'KPI "%(kpi)s" has type %(type)s while a tuple was '
                                "expected.\n\nThis can be fixed by either:\n\t- "
                                "Changing the KPI value to a tuple of length "
                                "%(length)s\nor\n\t- Changing the "
                                "KPI to `multi` mode and giving an explicit "
                                "value for each sub-KPI.",
                                kpi=kpi.description,
                                type=type(vals[0]),
                                length=col.colspan,
                            )
                        )
                if len(drilldown_args) != col.colspan:
                    drilldown_args = [None] * col.colspan

                kpi_matrix.set_values(kpi, col_key, vals, drilldown_args)

                if (
                    name_error
                    or no_auto_expand_accounts
                    or not kpi.auto_expand_accounts
                ):
                    continue

                for (
                    account_id,
                    vals,
                    drilldown_args,
                    _name_error,
                ) in expression_evaluator.eval_expressions_by_account(
                    expressions, locals_dict
                ):
                    for drilldown_arg in drilldown_args:
                        if not drilldown_arg:
                            continue
                        drilldown_arg["period_id"] = col_key
                        drilldown_arg["kpi_id"] = kpi.id
                    kpi_matrix.set_values_detail_account(
                        kpi, col_key, account_id, vals, drilldown_args
                    )

            if len(recompute_queue) == 0:
                # nothing to recompute, we are done
                break
            if len(recompute_queue) == len(compute_queue):
                # could not compute anything in this iteration
                # (ie real Name errors or cyclic dependency)
                # so we stop trying
                break
            # try again
            compute_queue = recompute_queue
            recompute_queue = []

    def declare_and_compute_period(
        self,
        kpi_matrix,
        col_key,
        col_label,
        col_description,
        aep,
        date_from,
        date_to,
        subkpis_filter=None,
        get_additional_move_line_filter=None,
        get_additional_query_filter=None,
        locals_dict=None,
        aml_model=None,
        no_auto_expand_accounts=False,
    ):
        _logger.warning(
            "declare_and_compute_period() is deprecated, "
            "use _declare_and_compute_period() instead"
        )
        expression_evaluator = ExpressionEvaluator(
            aep,
            date_from,
            date_to,
            get_additional_move_line_filter()
            if get_additional_move_line_filter
            else None,
            aml_model,
        )
        return self._declare_and_compute_period(
            expression_evaluator,
            kpi_matrix,
            col_key,
            col_label,
            col_description,
            subkpis_filter,
            get_additional_query_filter,
            locals_dict,
            no_auto_expand_accounts,
        )

    def _declare_and_compute_period(
        self,
        expression_evaluator,
        kpi_matrix,
        col_key,
        col_label,
        col_description,
        subkpis_filter=None,
        get_additional_query_filter=None,
        locals_dict=None,
        no_auto_expand_accounts=False,
    ):
        """Evaluate a report for a given period, populating a KpiMatrix.

        :param expression_evaluator: an ExpressionEvaluator instance
        :param kpi_matrix: the KpiMatrix object to be populated created
                           with prepare_kpi_matrix()
        :param col_key: the period key to use when populating the KpiMatrix
        :param subkpis_filter: a list of subkpis to include in the evaluation
                               (if empty, use all subkpis)
        :param get_additional_query_filter: a bound method that takes a single
                                            query argument and returns a
                                            domain compatible with the query
                                            underlying model
        :param locals_dict: personalized locals dictionary used as evaluation
                            context for the KPI expressions
        :param no_auto_expand_accounts: disable expansion of account details
        """
        self.ensure_one()

        # prepare the localsdict
        if locals_dict is None:
            locals_dict = {}

        # Evaluate subreports
        for subreport in self.subreport_ids:
            subreport_locals_dict = subreport.subreport_id._evaluate(
                expression_evaluator, subkpis_filter, get_additional_query_filter
            )
            locals_dict[subreport.name] = AutoStruct(
                **{
                    srk.name: subreport_locals_dict.get(srk.name, AccountingNone)
                    for srk in subreport.subreport_id.kpi_ids
                }
            )

        locals_dict.update(self.prepare_locals_dict())
        locals_dict["date_from"] = fields.Date.from_string(
            expression_evaluator.date_from
        )
        locals_dict["date_to"] = fields.Date.from_string(expression_evaluator.date_to)

        # fetch non-accounting queries
        locals_dict.update(
            self._fetch_queries(
                expression_evaluator.date_from,
                expression_evaluator.date_to,
                get_additional_query_filter,
            )
        )

        # use AEP to do the accounting queries
        expression_evaluator.aep_do_queries()

        self._declare_and_compute_col(
            expression_evaluator,
            kpi_matrix,
            col_key,
            col_label,
            col_description,
            subkpis_filter,
            locals_dict,
            no_auto_expand_accounts,
        )

    def get_kpis_by_account_id(self, company):
        """Return { account_id: set(kpi) }"""
        aep = self._prepare_aep(company)
        res = defaultdict(set)
        for kpi in self.kpi_ids:
            for expression in kpi.expression_ids:
                if not expression.name:
                    continue
                account_ids = aep.get_account_ids_for_expr(expression.name)
                for account_id in account_ids:
                    res[account_id].add(kpi)
        return res

    @api.model
    def _supports_target_move_filter(self, aml_model_name):
        return "parent_state" in self.env[aml_model_name]._fields

    @api.model
    def _get_target_move_domain(self, target_move, aml_model_name):
        """
        Obtain a domain to apply on a move-line-like model, to get posted
        entries or return all of them (always excluding cancelled entries).

        :param: target_move: all|posted
        :param: aml_model_name: an optional move-line-like model name
                (defaults to account.move.line)
        """
        if not self._supports_target_move_filter(aml_model_name):
            return []

        if target_move == "posted":
            return [("parent_state", "=", "posted")]
        elif target_move == "all":
            # all (in Odoo 13+, there is also the cancel state that we must ignore)
            return [("parent_state", "in", ("posted", "draft"))]
        else:
            raise UserError(_("Unexpected value %s for target_move.") % (target_move,))

    def evaluate(
        self,
        aep,
        date_from,
        date_to,
        target_move="posted",
        aml_model=None,
        subkpis_filter=None,
        get_additional_move_line_filter=None,
        get_additional_query_filter=None,
    ):
        """Simplified method to evaluate a report over a time period.

        :param aep: an AccountingExpressionProcessor instance created
                    using _prepare_aep()
        :param date_from, date_to: the starting and ending date
        :param target_move: all|posted
        :param aml_model: the name of a model that is compatible with
                          account.move.line (default: account.move.line)
        :param subkpis_filter: a list of subkpis to include in the evaluation
                               (if empty, use all subkpis)
        :param get_additional_move_line_filter: a bound method that takes
                                                no arguments and returns
                                                a domain compatible with
                                                account.move.line
        :param get_additional_query_filter: a bound method that takes a single
                                            query argument and returns a
                                            domain compatible with the query
                                            underlying model
        :return: a dictionary where keys are KPI names, and values are the
                 evaluated results; some additional keys might be present:
                 these should be ignored as they might be removed in
                 the future.
        """
        additional_move_line_filter = self._get_target_move_domain(
            target_move, aml_model or "account.move.line"
        )
        if get_additional_move_line_filter:
            additional_move_line_filter.extend(get_additional_move_line_filter())
        expression_evaluator = ExpressionEvaluator(
            aep,
            date_from,
            date_to,
            additional_move_line_filter,
            aml_model,
        )
        return self._evaluate(
            expression_evaluator, subkpis_filter, get_additional_query_filter
        )

    def _evaluate(
        self,
        expression_evaluator,
        subkpis_filter=None,
        get_additional_query_filter=None,
    ):
        locals_dict = {}
        kpi_matrix = self.prepare_kpi_matrix()
        self._declare_and_compute_period(
            expression_evaluator,
            kpi_matrix,
            col_key=1,
            col_label="",
            col_description="",
            subkpis_filter=subkpis_filter,
            get_additional_query_filter=get_additional_query_filter,
            locals_dict=locals_dict,
            no_auto_expand_accounts=True,
        )
        return locals_dict
