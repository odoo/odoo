// @ts-check

import { _t } from "@web/core/l10n/translation";

import * as spreadsheet from "@odoo/o-spreadsheet";

const { arg, isMatrix, toJsDate, toString } = spreadsheet.helpers;
const { functionRegistry } = spreadsheet.registries;

/**
 * @typedef {import("@spreadsheet").CustomFunctionDescription} CustomFunctionDescription
 * @typedef {import("@odoo/o-spreadsheet").FPayload} FPayload
 */

//--------------------------------------------------------------------------
// Spreadsheet functions
//--------------------------------------------------------------------------

// ODOO.FILTER.VALUE

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
});

// ODOO.FILTER.VALUE.V18

const ODOO_FILTER_VALUE_V18 = /** @satisfies {CustomFunctionDescription} */ ({
    description: _t("Compatibility version of ODOO.FILTER.VALUE for v18 spreadsheets. Required for date filters. Optional for others."),
    args: [arg("filter_name (string)", _t("The label of the filter whose value to return."))],
    category: "Odoo",
    hidden: true,
    compute: function (filterName) {
        const filter = this.getters.getGlobalFilterByName(toString(filterName, this.locale));
        const value = this["ODOO.FILTER.VALUE"](filterName);
        if (filter?.type === "relation") {
            const csvIds = toString(value[0][0])
            if (!csvIds) {
                return value;
            }
            const ids = csvIds.split(",").map((id) => parseInt(id, 10));
            const result =  this.odooDataProvider.serverData.get(filter.modelName, "web_search_read", [
                [["id", "in", ids]],
                { display_name: {} },
            ])
            return result.records.map((record) => record.display_name).join(", ");
        }
        if (filter?.type !== "date" || !isMatrix(value)) {
            return value;
        }
        const startValue = value[0][0];
        const endValue = value[1][0];
        if (!toString(startValue) && !toString(endValue)) {
            return "";
        }
        const start = toJsDate(startValue, this.locale);
        const end = toJsDate(endValue, this.locale);
        const endOfMonth = toJsDate(this["MONTH.END"](endValue), this.locale);
        if (start.getDate() !== 1 || end.getDate() !== endOfMonth.getDate()) {
            return value;
        } else if (start.getMonth() === end.getMonth()) {
            return String(start.getMonth() + 1).padStart(2, "0") + "/" + start.getFullYear();
        } else if (end.getMonth() - start.getMonth() === 2) {
            const quarter = Math.floor(start.getMonth() / 3) + 1;
            return "Q" + quarter + "/" + start.getFullYear();
        } else if (start.getFullYear() === end.getFullYear()) {
            return toString(start.getFullYear(), this.locale);
        }
        return value;
    },
});

functionRegistry
    .add("ODOO.FILTER.VALUE", ODOO_FILTER_VALUE)
    .add("ODOO.FILTER.VALUE.V18", ODOO_FILTER_VALUE_V18);
