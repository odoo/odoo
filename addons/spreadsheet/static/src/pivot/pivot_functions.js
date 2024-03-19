/** @odoo-module **/
// @ts-check

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { range } from "@web/core/utils/numbers";
import { EvaluationError } from "@odoo/o-spreadsheet";

const { arg, toBoolean, toString, toNumber } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;
const { CellErrorType } = spreadsheet;

/**
 * @typedef {import("./pivot_table").SpreadsheetPivotTable} SpreadsheetPivotTable
 * @typedef {import("@spreadsheet").CustomFunctionDescription} CustomFunctionDescription
 * @typedef {import("@odoo/o-spreadsheet").FPayload} FPayload
 */

//--------------------------------------------------------------------------
// Spreadsheet functions
//--------------------------------------------------------------------------

/**
 * Get the pivot ID from the formula pivot ID.
 *
 * @param {string} pivotFormulaId ID of the pivot (as used in the formula)
 * @param {import("@spreadsheet").OdooGetters} getters
 * @returns {string}
 */
function getPivotId(pivotFormulaId, getters) {
    const pivotId = getters.getPivotId(pivotFormulaId);
    if (!pivotId) {
        throw new EvaluationError(sprintf(_t('There is no pivot with id "%s"'), pivotFormulaId));
    }
    return pivotId;
}

/**
 * @param {string} pivotId
 * @param {string} measure
 * @param {import("@spreadsheet").OdooGetters} getters
 */
function assertMeasureExist(pivotId, measure, getters) {
    const { measures } = getters.getPivotDefinition(pivotId);
    if (!measures.find((m) => m.name === measure)) {
        const validMeasures = `(${measures.map((m) => m.name).join(", ")})`;
        throw new EvaluationError(
            sprintf(
                _t("The argument %s is not a valid measure. Here are the measures: %s"),
                measure,
                validMeasures
            )
        );
    }
}

/**
 * @param {(string | number)[]} domain
 */
function assertDomainLength(domain) {
    if (domain.length % 2 !== 0) {
        throw new EvaluationError(_t("Function PIVOT takes an even number of arguments."));
    }
}

const ODOO_FILTER_VALUE = /** @satisfies {CustomFunctionDescription} */ ({
    description: _t("Return the current value of a spreadsheet filter."),
    args: [arg("filter_name (string)", _t("The label of the filter whose value to return."))],
    category: "Odoo",
    /**
     * @param {FPayload} filterName
     */
    compute: function (filterName) {
        const unEscapedFilterName = toString(filterName).replaceAll('\\"', '"');
        return this.getters.getFilterDisplayValue(unEscapedFilterName);
    },
    returns: ["STRING"],
});

const ODOO_PIVOT = /** @satisfies {CustomFunctionDescription} */ ({
    description: _t("Get the value from a pivot."),
    args: [
        arg("pivot_id (string)", _t("ID of the pivot.")),
        arg("measure_name (string)", _t("Name of the measure.")),
        arg("domain_field_name (string,optional,repeating)", _t("Field name.")),
        arg("domain_value (string,optional,repeating)", _t("Value.")),
    ],
    category: "Odoo",
    /**
     * @param {FPayload} formulaId
     * @param {FPayload} measureName
     * @param  {...FPayload} domain
     */
    compute: function (formulaId, measureName, ...domain) {
        const _pivotFormulaId = toString(formulaId);
        const measure = toString(measureName);
        const domainArgs = domain.map(toString);
        const pivotId = getPivotId(_pivotFormulaId, this.getters);
        assertMeasureExist(pivotId, measure, this.getters);
        assertDomainLength(domainArgs);
        const pivot = this.getters.getPivot(pivotId);
        const error = pivot.assertIsValid({ throwOnError: false });
        if (error) {
            return error;
        }
        const value = pivot.getPivotCellValue(measure, domainArgs);
        if (!value && !this.getters.areDomainArgsFieldsValid(pivotId, domainArgs)) {
            return {
                value: CellErrorType.GenericError,
                message: _t("Dimensions don't match the pivot definition"),
            };
        }
        if (measure === "__count") {
            return { value, format: "0" };
        }
        const format = pivot.getPivotMeasureFormat(measure);
        return { value, format };
    },
    returns: ["NUMBER", "STRING"],
});

const ODOO_PIVOT_HEADER = /** @satisfies {CustomFunctionDescription} */ ({
    description: _t("Get the header of a pivot."),
    args: [
        arg("pivot_id (string)", _t("ID of the pivot.")),
        arg("domain_field_name (string,optional,repeating)", _t("Field name.")),
        arg("domain_value (string,optional,repeating)", _t("Value.")),
    ],
    category: "Odoo",
    /**
     * @param {FPayload} pivotId
     * @param  {...FPayload} domain
     */
    compute: function (pivotId, ...domain) {
        const _pivotFormulaId = toString(pivotId);
        const domainArgs = domain.map(toString);
        const _pivotId = getPivotId(_pivotFormulaId, this.getters);
        assertDomainLength(domainArgs);
        const pivot = this.getters.getPivot(_pivotId);
        const error = pivot.assertIsValid({ throwOnError: false });
        if (error) {
            return error;
        }
        const fieldName = domainArgs.at(-2);
        const valueArg = domainArgs.at(-1);
        const format =
            !fieldName || fieldName === "measure" || valueArg === "false"
                ? undefined
                : pivot.getPivotFieldFormat(fieldName);
        if (
            !this.getters.areDomainArgsFieldsValid(
                _pivotId,
                fieldName === "measure" ? domainArgs.slice(0, -2) : domainArgs
            )
        ) {
            return {
                value: CellErrorType.GenericError,
                message: _t("Dimensions don't match the pivot definition"),
            };
        }
        return {
            value: pivot.computePivotHeaderValue(domainArgs),
            format,
        };
    },
    returns: ["NUMBER", "STRING"],
});

const ODOO_PIVOT_POSITION = /** @satisfies {CustomFunctionDescription} */ ({
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
});

const ODOO_PIVOT_TABLE = /** @satisfies {CustomFunctionDescription} */ ({
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
    /**
     * @param {FPayload} pivotId
     * @param {FPayload} rowCount
     * @param {FPayload} includeTotal
     * @param {FPayload} includeColumnHeaders
     */
    compute: function (
        pivotId,
        rowCount = { value: 10000 },
        includeTotal = { value: true },
        includeColumnHeaders = { value: true }
    ) {
        const _pivotFormulaId = toString(pivotId);
        const _pivotId = getPivotId(_pivotFormulaId, this.getters);
        const pivot = this.getters.getPivot(_pivotId);
        const error = pivot.assertIsValid({ throwOnError: false });
        if (error) {
            return error;
        }
        const table = pivot.getTableStructure();
        const _includeColumnHeaders = toBoolean(includeColumnHeaders);
        const cells = table.getPivotCells(toBoolean(includeTotal), _includeColumnHeaders);
        const headerRows = _includeColumnHeaders ? table.getNumberOfHeaderRows() : 0;
        const pivotTitle = this.getters.getPivotDisplayName(_pivotId);
        const _rowCount = toNumber(rowCount, this.locale);
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
                result[col].push(getPivotCellValueAndFormat.call(this, _pivotFormulaId, pivotCell));
            }
        }
        if (_includeColumnHeaders) {
            result[0][0] = { value: pivotTitle };
        }
        return result;
    },
    category: "Odoo",
    returns: ["RANGE<ANY>"],
});

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
    .add("PIVOT.VALUE", ODOO_PIVOT)
    .add("PIVOT.HEADER", ODOO_PIVOT_HEADER)
    .add("PIVOT.POSITION", ODOO_PIVOT_POSITION)
    .add("PIVOT", ODOO_PIVOT_TABLE);
