/** @odoo-module */

import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "@spreadsheet/list/list_actions";
import * as spreadsheet from "@odoo/o-spreadsheet";

const { clickableCellRegistry } = spreadsheet.registries;

clickableCellRegistry.add("list", {
    condition: SEE_RECORD_LIST_VISIBLE,
    execute: SEE_RECORD_LIST,
    sequence: 10,
});
