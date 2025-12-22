/** @odoo-module */
import { _t } from "@web/core/l10n/translation";

import * as spreadsheet from "@odoo/o-spreadsheet";

import { SEE_RECORDS_PIVOT, SEE_RECORDS_PIVOT_VISIBLE } from "./pivot_actions";
import { PivotOdooCorePlugin } from "./plugins/pivot_odoo_core_plugin";
import { PivotUIGlobalFilterPlugin } from "./plugins/pivot_ui_global_filter_plugin";

const { coreTypes, invalidateEvaluationCommands } = spreadsheet;

const { cellMenuRegistry } = spreadsheet.registries;

const { inverseCommandRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

coreTypes.add("UPDATE_ODOO_PIVOT_DOMAIN");

invalidateEvaluationCommands.add("UPDATE_ODOO_PIVOT_DOMAIN");

cellMenuRegistry.add("pivot_see_records", {
    name: _t("See records"),
    sequence: 175,
    execute: async (env) => {
        const position = env.model.getters.getActivePosition();
        await SEE_RECORDS_PIVOT(position, env);
    },
    isVisible: (env) => {
        const position = env.model.getters.getActivePosition();
        return SEE_RECORDS_PIVOT_VISIBLE(position, env.model.getters);
    },
    icon: "o-spreadsheet-Icon.SEE_RECORDS",
});

inverseCommandRegistry.add("UPDATE_ODOO_PIVOT_DOMAIN", identity);

export { PivotOdooCorePlugin, PivotUIGlobalFilterPlugin };
