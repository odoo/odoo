/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { range } from "@web/core/utils/numbers";
import { EvaluationError } from "@odoo/o-spreadsheet";

const { arg, toBoolean, toString, toNumber } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;
const { CellErrorType } = spreadsheet;

/**
 * @typedef {import("@spreadsheet/pivot/pivot_table.js").SpreadsheetPivotTable} SpreadsheetPivotTable
 */

//--------------------------------------------------------------------------
// Spreadsheet functions
//--------------------------------------------------------------------------

function assertPivotsExists(pivotId, getters) {
    if (!getters.isExistingPivot(pivotId)) {
        throw new EvaluationError(sprintf(_t('There is no pivot with id "%s"'), pivotId));
    }
}

function assertMeasureExist(pivotId, measure, getters) {
    const { measures } = getters.getPivotDefinition(pivotId);
    if (!measures.includes(measure)) {
        const validMeasures = `(${measures})`;
        throw new EvaluationError(
            sprintf(
                _t("The argument %s is not a valid measure. Here are the measures: %s"),
                measure,
                validMeasures
            )
        );
    }
}

function assertDomainLength(domain) {
    if (domain.length % 2 !== 0) {
        throw new EvaluationError(_t("Function PIVOT takes an even number of arguments."));
    }
}

const ODOO_FILTER_VALUE = {
    description: _t("Return the current value of a spreadsheet filter."),
    args: [arg("filter_name (string)", _t("The label of the filter whose value to return."))],
    category: "Odoo",
    compute: function (filterName) {
        return this.getters.getFilterDisplayValue(filterName.value);
    },
    returns: ["STRING"],
};

const ODOO_PIVOT = {
    description: _t("Get the value from a pivot."),
    args: [
        arg("pivot_id (string)", _t("ID of the pivot.")),
        arg("measure_name (string)", _t("Name of the measure.")),
        arg("domain_field_name (string,optional,repeating)", _t("Field name.")),
        arg("domain_value (string,optional,repeating)", _t("Value.")),
    ],
    category: "Odoo",
    compute: function (pivotId, measureName, ...domain) {
        pivotId = toString(pivotId);
        const measure = toString(measureName);
        const args = domain.map(toString);
        assertPivotsExists(pivotId, this.getters);
        assertMeasureExist(pivotId, measure, this.getters);
        assertDomainLength(args);
        const value = this.getters.getPivotCellValue(pivotId, measure, args);
        const field = this.getters.getPivotDataSource(pivotId).getField(measure);
        let format = undefined;
        if (field) {
            switch (field.type) {
                case "integer":
                    format = "0";
                    break;
                case "float":
                    format = "#,##0.00";
                    break;
                case "monetary":
                    format = this.getters.getCompanyCurrencyFormat() || "#,##0.00";
                    break;
            }
        }
        return { value, format };
    },
    returns: ["NUMBER", "STRING"],
};

const ODOO_PIVOT_HEADER = {
    description: _t("Get the header of a pivot."),
    args: [
        arg("pivot_id (string)", _t("ID of the pivot.")),
        arg("domain_field_name (string,optional,repeating)", _t("Field name.")),
        arg("domain_value (string,optional,repeating)", _t("Value.")),
    ],
    category: "Odoo",
    compute: function (pivotId, ...domain) {
        pivotId = toString(pivotId);
        const args = domain.map(toString);
        assertPivotsExists(pivotId, this.getters);
        assertDomainLength(args);
        const pivot = this.getters.getPivotDataSource(pivotId);
        return {
            value: this.getters.getDisplayedPivotHeaderValue(pivotId, args, this.locale),
            format: odooPivotHeaderFormat(pivot, args, this.locale),
        };
    },
    returns: ["NUMBER", "STRING"],
};

function odooPivotHeaderFormat(pivot, domains, locale) {
    const len = domains.length;
    if (!len) {
        return undefined;
    }
    const fieldName = toString(domains[len - 2]);
    const value = toString(domains[len - 1]);
    if (fieldName === "measure" || value === "false") {
        return undefined;
    }
    const { aggregateOperator, field } = pivot.parseGroupField(fieldName);
    switch (field.type) {
        case "integer":
            return "0";
        case "float":
        case "monetary":
            return "#,##0.00";
        case "date":
        case "datetime":
            switch (aggregateOperator) {
                case "day":
                    return locale.dateFormat;
                case "month":
                    return "mmmm yyyy";
                case "year":
                    return "0";
                case "week":
                case "quarter":
                    return undefined;
            }
            break;
        default:
            return undefined;
    }
}

const ODOO_PIVOT_POSITION = {
    description: _t("Get the absolute ID of an element in the pivot"),
    args: [
        arg("pivot_id (string)", _t("ID of the pivot.")),
        arg("field_name (string)", _t("Name of the field.")),
        arg("position (number)", _t("Position in the pivot")),
    ],
    compute: function () {
        return {
            value: CellErrorType.GenericError,
            message: _t(`[[FUNCTION_NAME]] cannot be called from the spreadsheet.`),
        };
    },
    returns: ["STRING"],
    hidden: true,
};

const ODOO_PIVOT_TABLE = {
    description: _t("Get a pivot table."),
    args: [
        arg("pivot_id (string)", _t("ID of the pivot.")),
        arg("row_count (number, optional, default=10000)", _t("number of rows")),
        arg(
            "include_total (boolean, default=TRUE)",
            _t("Whether to include total/sub-totals or not.")
        ),
        arg(
            "include_column_titles (boolean, default=TRUE)",
            _t("Whether to include the column titles or not.")
        ),
    ],
    compute: function (
        pivotId,
        rowCount = { value: 10000 },
        includeTotal = { value: true },
        includeColumnHeaders = { value: true }
    ) {
        const _pivotId = toString(pivotId);
        assertPivotsExists(_pivotId, this.getters);
        /** @type {SpreadsheetPivotTable} */
        const table = this.getters.getPivotTableStructure(_pivotId);
        const _includeColumnHeaders = toBoolean(includeColumnHeaders);
        const cells = table.getPivotCells(toBoolean(includeTotal), _includeColumnHeaders);
        const headerRows = _includeColumnHeaders ? table.getNumberOfHeaderRows() : 0;
        const pivotTitle = this.getters.getPivotDisplayName(_pivotId);
        const _rowCount = toNumber(rowCount);
        if (_rowCount < 0) {
            throw new EvaluationError(_t("The number of rows must be positive."));
        }
        const end = Math.min(headerRows + _rowCount, cells[0].length);
        if (end === 0) {
            return [[{ value: pivotTitle }]];
        }
        const tableWidth = cells.length;
        const tableRows = range(0, end);
        const result = [];
        for (const col of range(0, tableWidth)) {
            result[col] = [];
            for (const row of tableRows) {
                const pivotCell = cells[col][row];
                result[col].push(getPivotCellValueAndFormat.call(this, _pivotId, pivotCell));
            }
        }
        if (_includeColumnHeaders) {
            result[0][0] = { value: pivotTitle };
        }
        return result;
    },
    category: "Odoo",
    returns: ["RANGE<ANY>"],
};

function getPivotCellValueAndFormat(pivotId, pivotCell) {
    if (!pivotCell.domain) {
        return { value: "", format: undefined };
    } else {
        const domain = pivotCell.domain;
        const measure = pivotCell.measure;
        const fn = pivotCell.isHeader ? ODOO_PIVOT_HEADER : ODOO_PIVOT;
        const args = pivotCell.isHeader ? [pivotId, ...domain] : [pivotId, measure, ...domain];
        return fn.compute.call(this, ...args);
    }
}

functionRegistry
    .add("ODOO.FILTER.VALUE", ODOO_FILTER_VALUE)
    .add("ODOO.PIVOT", ODOO_PIVOT)
    .add("ODOO.PIVOT.HEADER", ODOO_PIVOT_HEADER)
    .add("ODOO.PIVOT.POSITION", ODOO_PIVOT_POSITION)
    .add("ODOO.PIVOT.TABLE", ODOO_PIVOT_TABLE);
