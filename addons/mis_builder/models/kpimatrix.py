# Copyright 2014 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from collections import OrderedDict, defaultdict

from odoo import _
from odoo.exceptions import UserError

from .accounting_none import AccountingNone
from .mis_kpi_data import ACC_SUM
from .mis_safe_eval import DataError, mis_safe_eval
from .simple_array import SimpleArray

_logger = logging.getLogger(__name__)


class KpiMatrixRow:
    # TODO: ultimately, the kpi matrix will become ignorant of KPI's and
    #       accounts and know about rows, columns, sub columns and styles only.
    #       It is already ignorant of period and only knowns about columns.
    #       This will require a correct abstraction for expanding row details.

    def __init__(self, matrix, kpi, account_id=None, parent_row=None):
        self._matrix = matrix
        self.kpi = kpi
        self.account_id = account_id
        self.description = ""
        self.parent_row = parent_row
        if not self.account_id:
            self.style_props = self._matrix._style_model.merge(
                [self.kpi.report_id.style_id, self.kpi.style_id]
            )
        else:
            self.style_props = self._matrix._style_model.merge(
                [self.kpi.report_id.style_id, self.kpi.auto_expand_accounts_style_id]
            )

    @property
    def label(self):
        if not self.account_id:
            return self.kpi.description
        else:
            return self._matrix.get_account_name(self.account_id)

    @property
    def row_id(self):
        if not self.account_id:
            return self.kpi.name
        else:
            return f"{self.kpi.name}:{self.account_id}"

    def iter_cell_tuples(self, cols=None):
        if cols is None:
            cols = self._matrix.iter_cols()
        for col in cols:
            yield col.get_cell_tuple_for_row(self)

    def iter_cells(self, subcols=None):
        if subcols is None:
            subcols = self._matrix.iter_subcols()
        for subcol in subcols:
            yield subcol.get_cell_for_row(self)

    def is_empty(self):
        for cell in self.iter_cells():
            if cell and cell.val not in (AccountingNone, None):
                return False
        return True


class KpiMatrixCol:
    def __init__(self, key, label, description, locals_dict, subkpis):
        self.key = key
        self.label = label
        self.description = description
        self.locals_dict = locals_dict
        self.colspan = subkpis and len(subkpis) or 1
        self._subcols = []
        self.subkpis = subkpis
        if not subkpis:
            subcol = KpiMatrixSubCol(self, "", "", 0)
            self._subcols.append(subcol)
        else:
            for i, subkpi in enumerate(subkpis):
                subcol = KpiMatrixSubCol(self, subkpi.description, "", i)
                self._subcols.append(subcol)
        self._cell_tuples_by_row = {}  # {row: (cells tuple)}

    def _set_cell_tuple(self, row, cell_tuple):
        self._cell_tuples_by_row[row] = cell_tuple

    def iter_subcols(self):
        return self._subcols

    def iter_cell_tuples(self):
        return self._cell_tuples_by_row.values()

    def get_cell_tuple_for_row(self, row):
        return self._cell_tuples_by_row.get(row)


class KpiMatrixSubCol:
    def __init__(self, col, label, description, index=0):
        self.col = col
        self.label = label
        self.description = description
        self.index = index

    @property
    def subkpi(self):
        if self.col.subkpis:
            return self.col.subkpis[self.index]

    def iter_cells(self):
        for cell_tuple in self.col.iter_cell_tuples():
            yield cell_tuple[self.index]

    def get_cell_for_row(self, row):
        cell_tuple = self.col.get_cell_tuple_for_row(row)
        if cell_tuple is None:
            return None
        return cell_tuple[self.index]


class KpiMatrixCell:  # noqa: B903 (immutable data class)
    def __init__(
        self,
        row,
        subcol,
        val,
        val_rendered,
        val_comment,
        style_props,
        drilldown_arg,
        val_type,
    ):
        self.row = row
        self.subcol = subcol
        self.val = val
        self.val_rendered = val_rendered
        self.val_comment = val_comment
        self.style_props = style_props
        self.drilldown_arg = drilldown_arg
        self.val_type = val_type


class KpiMatrix:
    def __init__(self, env, multi_company=False, account_model="account.account"):
        # cache language id for faster rendering
        lang_model = env["res.lang"]
        self.lang = lang_model._lang_get(env.user.lang)
        self._style_model = env["mis.report.style"]
        self._account_model = env[account_model]
        # data structures
        # { kpi: KpiMatrixRow }
        self._kpi_rows = OrderedDict()
        # { kpi: {account_id: KpiMatrixRow} }
        self._detail_rows = {}
        # { col_key: KpiMatrixCol }
        self._cols = OrderedDict()
        # { col_key (left of comparison): [(col_key, base_col_key)] }
        self._comparison_todo = defaultdict(list)
        # { col_key (left of sum): (col_key, [(sign, sum_col_key)])
        self._sum_todo = {}
        # { account_id: account_name }
        self._account_names = {}
        self._multi_company = multi_company

    def declare_kpi(self, kpi):
        """Declare a new kpi (row) in the matrix.

        Invoke this first for all kpi, in display order.
        """
        self._kpi_rows[kpi] = KpiMatrixRow(self, kpi)
        self._detail_rows[kpi] = {}

    def declare_col(self, col_key, label, description, locals_dict, subkpis):
        """Declare a new column, giving it an identifier (key).

        Invoke the declare_* methods in display order.
        """
        col = KpiMatrixCol(col_key, label, description, locals_dict, subkpis)
        self._cols[col_key] = col
        return col

    def declare_comparison(
        self, cmpcol_key, col_key, base_col_key, label, description=None
    ):
        """Declare a new comparison column.

        Invoke the declare_* methods in display order.
        """
        self._comparison_todo[cmpcol_key] = (col_key, base_col_key, label, description)
        self._cols[cmpcol_key] = None  # reserve slot in insertion order

    def declare_sum(
        self, sumcol_key, col_to_sum_keys, label, description=None, sum_accdet=False
    ):
        """Declare a new summation column.

        Invoke the declare_* methods in display order.
        :param col_to_sum_keys: [(sign, col_key)]
        """
        self._sum_todo[sumcol_key] = (col_to_sum_keys, label, description, sum_accdet)
        self._cols[sumcol_key] = None  # reserve slot in insertion order

    def set_values(self, kpi, col_key, vals, drilldown_args, tooltips=True):
        """Set values for a kpi and a colum.

        Invoke this after declaring the kpi and the column.
        """
        self.set_values_detail_account(
            kpi, col_key, None, vals, drilldown_args, tooltips
        )

    def set_values_detail_account(
        self, kpi, col_key, account_id, vals, drilldown_args, tooltips=True
    ):
        """Set values for a kpi and a column and a detail account.

        Invoke this after declaring the kpi and the column.
        """
        if not account_id:
            row = self._kpi_rows[kpi]
        else:
            kpi_row = self._kpi_rows[kpi]
            if account_id in self._detail_rows[kpi]:
                row = self._detail_rows[kpi][account_id]
            else:
                row = KpiMatrixRow(self, kpi, account_id, parent_row=kpi_row)
                self._detail_rows[kpi][account_id] = row
        col = self._cols[col_key]
        cell_tuple = []
        assert len(vals) == col.colspan
        assert len(drilldown_args) == col.colspan
        for val, drilldown_arg, subcol in zip(vals, drilldown_args, col.iter_subcols()):  # noqa: B905
            if isinstance(val, DataError):
                val_rendered = val.name
                val_comment = val.msg
            else:
                val_rendered = self._style_model.render(
                    self.lang, row.style_props, kpi.type, val
                )
                if row.kpi.multi and subcol.subkpi:
                    val_comment = "{}.{} = {}".format(
                        row.kpi.name,
                        subcol.subkpi.name,
                        row.kpi._get_expression_str_for_subkpi(subcol.subkpi),
                    )
                else:
                    val_comment = f"{row.kpi.name} = {row.kpi.expression}"
            cell_style_props = row.style_props
            if row.kpi.style_expression:
                # evaluate style expression
                try:
                    style_name = mis_safe_eval(
                        row.kpi.style_expression, col.locals_dict
                    )
                except Exception:
                    _logger.error(
                        "Error evaluating style expression <%s>",
                        row.kpi.style_expression,
                        exc_info=True,
                    )
                if style_name:
                    style = self._style_model.search([("name", "=", style_name)])
                    if style:
                        cell_style_props = self._style_model.merge(
                            [row.style_props, style[0]]
                        )
                    else:
                        _logger.error("Style '%s' not found.", style_name)
            cell = KpiMatrixCell(
                row,
                subcol,
                val,
                val_rendered,
                tooltips and val_comment or None,
                cell_style_props,
                drilldown_arg,
                kpi.type,
            )
            cell_tuple.append(cell)
        assert len(cell_tuple) == col.colspan
        col._set_cell_tuple(row, cell_tuple)

    def _common_subkpis(self, cols):
        if not cols:
            return set()
        common_subkpis = set(cols[0].subkpis)
        for col in cols[1:]:
            common_subkpis = common_subkpis & set(col.subkpis)
        return common_subkpis

    def compute_comparisons(self):
        """Compute comparisons.

        Invoke this after setting all values.
        """
        for (
            cmpcol_key,
            (col_key, base_col_key, label, description),
        ) in self._comparison_todo.items():
            col = self._cols[col_key]
            base_col = self._cols[base_col_key]
            common_subkpis = self._common_subkpis([col, base_col])
            if (col.subkpis or base_col.subkpis) and not common_subkpis:
                raise UserError(
                    _(
                        "Columns %(descr)s and %(base_descr)s are not comparable",
                        descr=col.description,
                        base_descr=base_col.description,
                    )
                )
            if not label:
                label = f"{col.label} vs {base_col.label}"
            comparison_col = KpiMatrixCol(
                cmpcol_key,
                label,
                description,
                {},
                sorted(common_subkpis, key=lambda s: s.sequence),
            )
            self._cols[cmpcol_key] = comparison_col
            for row in self.iter_rows():
                cell_tuple = col.get_cell_tuple_for_row(row)
                base_cell_tuple = base_col.get_cell_tuple_for_row(row)
                if cell_tuple is None and base_cell_tuple is None:
                    continue
                if cell_tuple is None:
                    vals = [AccountingNone] * (len(common_subkpis) or 1)
                else:
                    vals = [
                        cell.val
                        for cell in cell_tuple
                        if not common_subkpis or cell.subcol.subkpi in common_subkpis
                    ]
                if base_cell_tuple is None:
                    base_vals = [AccountingNone] * (len(common_subkpis) or 1)
                else:
                    base_vals = [
                        cell.val
                        for cell in base_cell_tuple
                        if not common_subkpis or cell.subcol.subkpi in common_subkpis
                    ]
                comparison_cell_tuple = []
                for val, base_val, comparison_subcol in zip(  # noqa: B905
                    vals,
                    base_vals,
                    comparison_col.iter_subcols(),
                ):
                    # TODO FIXME average factors
                    comparison = self._style_model.compare_and_render(
                        self.lang,
                        row.style_props,
                        row.kpi.type,
                        row.kpi.compare_method,
                        val,
                        base_val,
                        1,
                        1,
                    )
                    delta, delta_r, delta_style, delta_type = comparison
                    comparison_cell_tuple.append(
                        KpiMatrixCell(
                            row,
                            comparison_subcol,
                            delta,
                            delta_r,
                            None,
                            delta_style,
                            None,
                            delta_type,
                        )
                    )
                comparison_col._set_cell_tuple(row, comparison_cell_tuple)

    def compute_sums(self):
        """Compute comparisons.

        Invoke this after setting all values.
        """
        for (
            sumcol_key,
            (col_to_sum_keys, label, description, sum_accdet),
        ) in self._sum_todo.items():
            sumcols = [self._cols[k] for (sign, k) in col_to_sum_keys]
            # TODO check all sumcols are resolved; we need a kind of
            #      recompute queue here so we don't depend on insertion
            #      order
            common_subkpis = self._common_subkpis(sumcols)
            if any(c.subkpis for c in sumcols) and not common_subkpis:
                raise UserError(
                    _(
                        "Sum cannot be computed in column {} "
                        "because the columns to sum have no "
                        "common subkpis"
                    ).format(label)
                )
            sum_col = KpiMatrixCol(
                sumcol_key,
                label,
                description,
                {},
                sorted(common_subkpis, key=lambda s: s.sequence),
            )
            self._cols[sumcol_key] = sum_col
            for row in self.iter_rows():
                acc = SimpleArray([AccountingNone] * (len(common_subkpis) or 1))
                if row.kpi.accumulation_method == ACC_SUM and not (
                    row.account_id and not sum_accdet
                ):
                    for sign, col_to_sum in col_to_sum_keys:
                        cell_tuple = self._cols[col_to_sum].get_cell_tuple_for_row(row)
                        if cell_tuple is None:
                            vals = [AccountingNone] * (len(common_subkpis) or 1)
                        else:
                            vals = [
                                cell.val
                                for cell in cell_tuple
                                if not common_subkpis
                                or cell.subcol.subkpi in common_subkpis
                            ]
                        if sign == "+":
                            acc += SimpleArray(vals)
                        else:
                            acc -= SimpleArray(vals)
                self.set_values_detail_account(
                    row.kpi,
                    sumcol_key,
                    row.account_id,
                    acc,
                    [None] * (len(common_subkpis) or 1),
                    tooltips=False,
                )

    def iter_rows(self):
        """Iterate rows in display order.

        yields KpiMatrixRow.
        """
        for kpi_row in self._kpi_rows.values():
            yield kpi_row
            detail_rows = self._detail_rows[kpi_row.kpi].values()
            detail_rows = sorted(detail_rows, key=lambda r: r.label)
            yield from detail_rows

    def iter_cols(self):
        """Iterate columns in display order.

        yields KpiMatrixCol: one for each column or comparison.
        """
        for _col_key, col in self._cols.items():
            yield col

    def iter_subcols(self):
        """Iterate sub columns in display order.

        yields KpiMatrixSubCol: one for each subkpi in each column
        and comparison.
        """
        for col in self.iter_cols():
            yield from col.iter_subcols()

    def _load_account_names(self):
        account_ids = set()
        for detail_rows in self._detail_rows.values():
            account_ids.update(detail_rows.keys())
        accounts = self._account_model.search([("id", "in", list(account_ids))])
        self._account_names = {a.id: self._get_account_name(a) for a in accounts}

    def _get_account_name(self, account):
        result = f"{account.code} {account.name}"
        if self._multi_company:
            result = f"{result} [{account.company_id.name}]"
        return result

    def get_account_name(self, account_id):
        if account_id not in self._account_names:
            self._load_account_names()
        return self._account_names[account_id]

    def as_dict(self):
        header = [{"cols": []}, {"cols": []}]
        for col in self.iter_cols():
            header[0]["cols"].append(
                {
                    "label": col.label,
                    "description": col.description,
                    "colspan": col.colspan,
                }
            )
            for subcol in col.iter_subcols():
                header[1]["cols"].append(
                    {
                        "label": subcol.label,
                        "description": subcol.description,
                        "colspan": 1,
                    }
                )

        body = []
        for row in self.iter_rows():
            if (
                row.style_props.hide_empty and row.is_empty()
            ) or row.style_props.hide_always:
                continue
            row_data = {
                "row_id": row.row_id,
                "parent_row_id": (row.parent_row and row.parent_row.row_id or None),
                "label": row.label,
                "description": row.description,
                "style": self._style_model.to_css_style(row.style_props),
                "cells": [],
            }
            for cell in row.iter_cells():
                if cell is None:
                    # TODO use subcol style here
                    row_data["cells"].append({})
                else:
                    if cell.val is AccountingNone or isinstance(cell.val, DataError):
                        val = None
                    else:
                        val = cell.val
                    col_data = {
                        "val": val,
                        "val_r": cell.val_rendered,
                        "val_c": cell.val_comment,
                        "style": self._style_model.to_css_style(
                            cell.style_props, no_indent=True
                        ),
                    }
                    if cell.drilldown_arg:
                        col_data["drilldown_arg"] = cell.drilldown_arg
                    row_data["cells"].append(col_data)
            body.append(row_data)

        return {"header": header, "body": body}
