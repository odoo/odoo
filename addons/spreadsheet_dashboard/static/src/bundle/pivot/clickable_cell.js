/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import {
    SEE_RECORDS_PIVOT,
    SEE_RECORDS_PIVOT_VISIBLE,
    SET_FILTER_MATCHING,
    SET_FILTER_MATCHING_CONDITION,
} from "@spreadsheet/pivot/pivot_actions";

const { clickableCellRegistry } = spreadsheet.registries;

clickableCellRegistry.add("pivot", {
    condition: SEE_RECORDS_PIVOT_VISIBLE,
    execute: SEE_RECORDS_PIVOT,
    sequence: 3,
});

clickableCellRegistry.add("pivot_set_filter_matching", {
    condition: SET_FILTER_MATCHING_CONDITION,
    execute: SET_FILTER_MATCHING,
    sequence: 2,
});
