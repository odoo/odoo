/** @odoo-module */

import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "@spreadsheet/list/list_actions";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

const { clickableCellRegistry } = spreadsheet.registries;

clickableCellRegistry.add("list", {
    condition: SEE_RECORD_LIST_VISIBLE,
    action: SEE_RECORD_LIST,
    sequence: 10,
});
