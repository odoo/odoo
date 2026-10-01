import { _t } from "@web/core/l10n/translation";

import * as spreadsheet from "@odoo/o-spreadsheet";

import { SEE_RECORDS_PIVOT, SEE_RECORDS_PIVOT_VISIBLE } from "./pivot_actions";
import { PivotOdooCorePlugin } from "./plugins/pivot_odoo_core_plugin";
import { PivotCoreViewGlobalFilterPlugin } from "./plugins/pivot_core_view_global_filter_plugin";

const { registerCommand, invalidateEvaluationCommands } = spreadsheet;

const { cellMenuRegistry } = spreadsheet.registries;

// this command is deprecated. use UPDATE_PIVOT instead
registerCommand("UPDATE_ODOO_PIVOT_DOMAIN", {
    category: "core",
    invalidatesEvaluation: true,
});

// `REFRESH_PIVOT` is an o-spreadsheet command: it is already registered, only
// its behaviour is extended here.
invalidateEvaluationCommands.add("REFRESH_PIVOT");

cellMenuRegistry.add("pivot_see_records", {
    name: _t("See records"),
    sequence: 175,
    execute: async (env, isMiddleClick) => {
        const position = env.model.getters.getActivePosition();
        await SEE_RECORDS_PIVOT(position, env, isMiddleClick);
    },
    isVisible: (env) => {
        const position = env.model.getters.getActivePosition();
        return SEE_RECORDS_PIVOT_VISIBLE(position, env.model.getters);
    },
    icon: "o-spreadsheet-Icon.SEE_RECORDS",
    isEnabledOnLockedSheet: true,
});

export { PivotOdooCorePlugin, PivotCoreViewGlobalFilterPlugin };
