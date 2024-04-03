/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { SEE_RECORDS_PIVOT, SEE_RECORDS_PIVOT_VISIBLE } from "@spreadsheet/pivot/pivot_actions";
import { getFirstPivotFunction } from "@spreadsheet/pivot/pivot_helpers";

const { clickableCellRegistry } = spreadsheet.registries;

clickableCellRegistry.add("pivot", {
    condition: SEE_RECORDS_PIVOT_VISIBLE,
    action: SEE_RECORDS_PIVOT,
    sequence: 3,
});

clickableCellRegistry.add("pivot_set_filter_matching", {
    condition: (cell, env) => {
        return (
            SEE_RECORDS_PIVOT_VISIBLE(cell) &&
            getFirstPivotFunction(cell.content).functionName === "ODOO.PIVOT.HEADER" &&
            env.model.getters.getFiltersMatchingPivot(cell.content).length > 0
        );
    },
    action: (cell, env) => {
        const filters = env.model.getters.getFiltersMatchingPivot(cell.content);
        env.model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
    },
    sequence: 2,
});
