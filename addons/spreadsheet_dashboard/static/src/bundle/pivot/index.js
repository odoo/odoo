/** @odoo-module */
import { _lt } from "@web/core/l10n/translation";

import { SEE_RECORDS_PIVOT, SEE_RECORDS_PIVOT_VISIBLE } from "@spreadsheet/pivot/pivot_actions";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

const { dashboardMenuRegistry } = spreadsheet.registries;

dashboardMenuRegistry.add("see_records_pivot", {
    name: _lt("See records"),
    sequence: 10,
    action: SEE_RECORDS_PIVOT,
    isReadonlyAllowed: true,
    isVisible: SEE_RECORDS_PIVOT_VISIBLE,
});
