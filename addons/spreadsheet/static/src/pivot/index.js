/** @odoo-module */
import { _t } from "@web/core/l10n/translation";

import * as spreadsheet from "@odoo/o-spreadsheet";

import { PivotCorePlugin } from "./plugins/pivot_core_plugin";
import { PivotUIPlugin } from "./plugins/pivot_ui_plugin";

import { SEE_RECORDS_PIVOT, SEE_RECORDS_PIVOT_VISIBLE } from "./pivot_actions";
import { PivotOdooCorePlugin } from "./plugins/pivot_odoo_core_plugin";
import { PivotUIGlobalFilterPlugin } from "./plugins/pivot_ui_global_filter_plugin";

const { coreTypes, invalidateEvaluationCommands } = spreadsheet;

const { cellMenuRegistry } = spreadsheet.registries;

const { inverseCommandRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

coreTypes.add("ADD_PIVOT");
coreTypes.add("INSERT_PIVOT");
coreTypes.add("RENAME_PIVOT");
coreTypes.add("REMOVE_PIVOT");
coreTypes.add("UPDATE_ODOO_PIVOT_DOMAIN");
coreTypes.add("UPDATE_PIVOT");
coreTypes.add("DUPLICATE_PIVOT");

invalidateEvaluationCommands.add("UPDATE_ODOO_PIVOT_DOMAIN");
invalidateEvaluationCommands.add("REMOVE_PIVOT");
invalidateEvaluationCommands.add("ADD_PIVOT");
invalidateEvaluationCommands.add("UPDATE_PIVOT");
invalidateEvaluationCommands.add("INSERT_PIVOT");
invalidateEvaluationCommands.add("RENAME_PIVOT");

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
    .add("ADD_PIVOT", identity)
    .add("INSERT_PIVOT", identity)
    .add("RENAME_PIVOT", identity)
    .add("REMOVE_PIVOT", identity)
    .add("UPDATE_PIVOT", identity)
    .add("UPDATE_ODOO_PIVOT_DOMAIN", identity);

export { PivotCorePlugin, PivotUIPlugin, PivotOdooCorePlugin, PivotUIGlobalFilterPlugin };
