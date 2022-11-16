/** @odoo-module */
import { _lt } from "@web/core/l10n/translation";

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

import PivotCorePlugin from "./plugins/pivot_core_plugin";
import PivotUIPlugin from "./plugins/pivot_ui_plugin";

import { SEE_RECORDS_PIVOT, SEE_RECORDS_PIVOT_VISIBLE } from "./pivot_actions";

const { coreTypes, invalidateEvaluationCommands } = spreadsheet;
const { cellMenuRegistry } = spreadsheet.registries;

const { inverseCommandRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

coreTypes.add("INSERT_PIVOT");
coreTypes.add("RENAME_ODOO_PIVOT");
coreTypes.add("REMOVE_PIVOT");
coreTypes.add("RE_INSERT_PIVOT");
coreTypes.add("UPDATE_ODOO_PIVOT_DOMAIN");

invalidateEvaluationCommands.add("UPDATE_ODOO_PIVOT_DOMAIN");
invalidateEvaluationCommands.add("REMOVE_PIVOT");
invalidateEvaluationCommands.add("INSERT_PIVOT");

cellMenuRegistry.add("pivot_see_records", {
    name: _lt("See records"),
    sequence: 175,
    action: async (env) => {
        const cell = env.model.getters.getActiveCell();
        await SEE_RECORDS_PIVOT(cell, env);
    },
    isVisible: (env) => {
        const cell = env.model.getters.getActiveCell();
        return SEE_RECORDS_PIVOT_VISIBLE(cell);
    },
});

inverseCommandRegistry
    .add("INSERT_PIVOT", identity)
    .add("RENAME_ODOO_PIVOT", identity)
    .add("REMOVE_PIVOT", identity)
    .add("UPDATE_ODOO_PIVOT_DOMAIN", identity)
    .add("RE_INSERT_PIVOT", identity);

export { PivotCorePlugin, PivotUIPlugin };
