/** @odoo-module */
import { _lt } from "@web/core/l10n/translation";

import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "@spreadsheet/list/list_actions";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

const { dashboardMenuRegistry } = spreadsheet.registries;

dashboardMenuRegistry.add("see_records_list", {
    name: _lt("See record"),
    sequence: 20,
    action: SEE_RECORD_LIST,
    isReadonlyAllowed: true,
    isVisible: SEE_RECORD_LIST_VISIBLE,
});
