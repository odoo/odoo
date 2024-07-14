/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
const { otRegistry } = spreadsheet.registries;
const { transformRangeData } = spreadsheet.helpers;

otRegistry.addTransformation(
    "REMOVE_GLOBAL_FILTER",
    ["EDIT_GLOBAL_FILTER"],
    (toTransform, executed) => (toTransform.filter.id === executed.id ? undefined : toTransform)
);

otRegistry.addTransformation(
    "REMOVE_COLUMNS_ROWS",
    ["EDIT_GLOBAL_FILTER", "ADD_GLOBAL_FILTER"],
    transformTextFilterRange
);
otRegistry.addTransformation(
    "ADD_COLUMNS_ROWS",
    ["EDIT_GLOBAL_FILTER", "ADD_GLOBAL_FILTER"],
    transformTextFilterRange
);

function transformTextFilterRange(toTransform, executed) {
    const filter = toTransform.filter;
    if (filter.type === "text" && filter.rangeOfAllowedValues) {
        const transformedRange = transformRangeData(filter.rangeOfAllowedValues, executed);
        if (transformedRange) {
            return {
                ...toTransform,
                filter: {
                    ...filter,
                    rangeOfAllowedValues: transformedRange,
                },
            };
        }
    }
    return toTransform;
}
