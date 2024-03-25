/** @odoo-module **/
// @ts-check

import { _t } from "@web/core/l10n/translation";

import * as spreadsheet from "@odoo/o-spreadsheet";

const { arg, toString } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;
const { CellErrorType } = spreadsheet;

/**
 * @typedef {import("@spreadsheet").CustomFunctionDescription} CustomFunctionDescription
 * @typedef {import("@odoo/o-spreadsheet").FPayload} FPayload
 */

//--------------------------------------------------------------------------
// Spreadsheet functions
//--------------------------------------------------------------------------

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

functionRegistry
    .add("ODOO.FILTER.VALUE", ODOO_FILTER_VALUE)
    .add("PIVOT.POSITION", ODOO_PIVOT_POSITION);
