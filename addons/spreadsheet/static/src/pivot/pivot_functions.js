/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
const { args, toString } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;

//--------------------------------------------------------------------------
// Spreadsheet functions
//--------------------------------------------------------------------------

function assertPivotsExists(pivotId, getters) {
    if (!getters.isExistingPivot(pivotId)) {
        throw new Error(sprintf(_t('There is no pivot with id "%s"'), pivotId));
    }
}

function assertMeasureExist(pivotId, measure, getters) {
    const { measures } = getters.getPivotDefinition(pivotId);
    if (!measures.includes(measure)) {
        const validMeasures = `(${measures})`;
        throw new Error(
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
        throw new Error(_t("Function PIVOT takes an even number of arguments."));
    }
}

functionRegistry
    .add("ODOO.FILTER.VALUE", {
        description: _t("Return the current value of a spreadsheet filter."),
        args: args(`
            filter_name (string) ${_t("The label of the filter whose value to return.")}
        `),
        compute: function (filterName) {
            const unEscapedFilterName = toString(filterName).replaceAll('\\"', '"');
            return this.getters.getFilterDisplayValue(unEscapedFilterName);
        },
        returns: ["STRING"],
    })
    .add("ODOO.PIVOT", {
        description: _t("Get the value from a pivot."),
        args: args(`
            pivot_id (string) ${_t("ID of the pivot.")}
            measure_name (string) ${_t("Name of the measure.")}
            domain_field_name (string,optional,repeating) ${_t("Field name.")}
            domain_value (string,optional,repeating) ${_t("Value.")}
        `),
        compute: function (pivotId, measureName, ...domain) {
            pivotId = toString(pivotId);
            const measure = toString(measureName);
            const args = domain.map(toString);
            assertPivotsExists(pivotId, this.getters);
            assertMeasureExist(pivotId, measure, this.getters);
            assertDomainLength(args);
            return this.getters.getPivotCellValue(pivotId, measure, args);
        },
        computeFormat: function (pivotId, measureName, ...domain) {
            pivotId = toString(pivotId.value);
            const measure = toString(measureName.value);
            const field = this.getters.getPivotDataSource(pivotId).getReportMeasures()[measure];
            if (!field) {
                return undefined;
            }
            switch (field.type) {
                case "integer":
                    return "0";
                case "float":
                    return "#,##0.00";
                case "monetary":
                    return this.getters.getCompanyCurrencyFormat() || "#,##0.00";
                default:
                    return undefined;
            }
        },
        returns: ["NUMBER", "STRING"],
    })
    .add("ODOO.PIVOT.HEADER", {
        description: _t("Get the header of a pivot."),
        args: args(`
            pivot_id (string) ${_t("ID of the pivot.")}
            domain_field_name (string,optional,repeating) ${_t("Field name.")}
            domain_value (string,optional,repeating) ${_t("Value.")}
        `),
        compute: function (pivotId, ...domain) {
            pivotId = toString(pivotId);
            const args = domain.map(toString);
            assertPivotsExists(pivotId, this.getters);
            assertDomainLength(args);
            return this.getters.getDisplayedPivotHeaderValue(pivotId, args);
        },
        computeFormat: function (pivotId, ...domain) {
            pivotId = toString(pivotId.value);
            const pivot = this.getters.getPivotDataSource(pivotId);
            const len = domain.length;
            if (!len) {
                return undefined;
            }
            const fieldName = toString(domain[len - 2].value);
            const value = toString(domain[len - 1].value);
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
                    if (aggregateOperator === "day") {
                        return "mm/dd/yyyy";
                    }
                    return undefined;
                default:
                    return undefined;
            }
        },
        returns: ["NUMBER", "STRING"],
    })
    .add("ODOO.PIVOT.POSITION", {
        description: _t("Get the absolute ID of an element in the pivot"),
        args: args(`
            pivot_id (string) ${_t("ID of the pivot.")}
            field_name (string) ${_t("Name of the field.")}
            position (number) ${_t("Position in the pivot")}
        `),
        compute: function () {
            throw new Error(_t(`[[FUNCTION_NAME]] cannot be called from the spreadsheet.`));
        },
        returns: ["STRING"],
    });
