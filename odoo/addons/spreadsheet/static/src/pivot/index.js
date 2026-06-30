/** @odoo-module */
import { _t } from "@web/core/l10n/translation";

import * as spreadsheet from "@odoo/o-spreadsheet";

import { PivotCorePlugin } from "./plugins/pivot_core_plugin";
import { PivotUIPlugin } from "./plugins/pivot_ui_plugin";

import { SEE_RECORDS_PIVOT, SEE_RECORDS_PIVOT_VISIBLE } from "./pivot_actions";

const {
    coreTypes,
    invalidateEvaluationCommands,
    invalidateCFEvaluationCommands,
    invalidateDependenciesCommands,
} = spreadsheet;

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
invalidateEvaluationCommands.add("RENAME_ODOO_PIVOT");

invalidateDependenciesCommands.add("UPDATE_ODOO_PIVOT_DOMAIN");
invalidateDependenciesCommands.add("REMOVE_PIVOT");
invalidateDependenciesCommands.add("INSERT_PIVOT");
invalidateDependenciesCommands.add("RENAME_ODOO_PIVOT");

invalidateCFEvaluationCommands.add("UPDATE_ODOO_PIVOT_DOMAIN");
invalidateCFEvaluationCommands.add("REMOVE_PIVOT");
invalidateCFEvaluationCommands.add("INSERT_PIVOT");
invalidateCFEvaluationCommands.add("RENAME_ODOO_PIVOT");

cellMenuRegistry.add("pivot_see_records", {
    name: _t("See records"),
    sequence: 175,
    execute: async (env) => {
        const position = env.model.getters.getActivePosition();
        await SEE_RECORDS_PIVOT(position, env);
    },
    isVisible: (env) => {
        const position = env.model.getters.getActivePosition();
        return SEE_RECORDS_PIVOT_VISIBLE(position, env);
    },
    icon: "o-spreadsheet-Icon.SEE_RECORDS",
});

inverseCommandRegistry
    .add("INSERT_PIVOT", identity)
    .add("RENAME_ODOO_PIVOT", identity)
    .add("REMOVE_PIVOT", identity)
    .add("UPDATE_ODOO_PIVOT_DOMAIN", identity)
    .add("RE_INSERT_PIVOT", identity);

export { PivotCorePlugin, PivotUIPlugin };
