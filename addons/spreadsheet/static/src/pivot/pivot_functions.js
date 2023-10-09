/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

import * as spreadsheet from "@odoo/o-spreadsheet";
const { arg, toString } = spreadsheet.helpers;
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

const ODOO_FILTER_VALUE = {
    description: _t("Return the current value of a spreadsheet filter."),
    args: [arg("filter_name (string)", _t("The label of the filter whose value to return."))],
    category: "Odoo",
    compute: function (filterName) {
        return this.getters.getFilterDisplayValue(filterName);
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
    compute: function (pivotId, measureName, ...domain) {
        pivotId = toString(pivotId);
        const measure = toString(measureName);
        const args = domain.map(toString);
        assertPivotsExists(pivotId, this.getters);
        assertMeasureExist(pivotId, measure, this.getters);
        assertDomainLength(args);
        return this.getters.getPivotCellValue(pivotId, measure, args);
    },
    category: "Odoo",
    computeFormat: function (pivotId, measureName, ...domain) {
        pivotId = toString(pivotId.value);
        const measure = toString(measureName.value);
        const field = this.getters.getPivotDataSource(pivotId).getField(measure);
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
        return this.getters.getDisplayedPivotHeaderValue(pivotId, args, this.locale);
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
                switch (aggregateOperator) {
                    case "day":
                        return this.locale.dateFormat;
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
    },
    returns: ["NUMBER", "STRING"],
};

const ODOO_PIVOT_POSITION = {
    description: _t("Get the absolute ID of an element in the pivot"),
    args: [
        arg("pivot_id (string)", _t("ID of the pivot.")),
        arg("field_name (string)", _t("Name of the field.")),
        arg("position (number)", _t("Position in the pivot")),
    ],
    compute: function () {
        throw new Error(_t(`[[FUNCTION_NAME]] cannot be called from the spreadsheet.`));
    },
    returns: ["STRING"],
    hidden: true,
};

functionRegistry
    .add("ODOO.FILTER.VALUE", ODOO_FILTER_VALUE)
    .add("ODOO.PIVOT", ODOO_PIVOT)
    .add("ODOO.PIVOT.HEADER", ODOO_PIVOT_HEADER)
    .add("ODOO.PIVOT.POSITION", ODOO_PIVOT_POSITION);
