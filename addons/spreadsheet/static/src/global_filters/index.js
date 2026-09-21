import * as spreadsheet from "@odoo/o-spreadsheet";

import { GlobalFiltersUIPlugin } from "./plugins/global_filters_ui_plugin";
import { GlobalFiltersCorePlugin } from "./plugins/global_filters_core_plugin";
import { GlobalFiltersCoreViewPlugin } from "./plugins/global_filters_core_view_plugin";
const { registerCommand } = spreadsheet;

registerCommand("ADD_GLOBAL_FILTER", {
    category: "core",
    invalidatesEvaluation: true,
    inverse: (cmd) => [
        {
            type: "REMOVE_GLOBAL_FILTER",
            id: cmd.filter.id,
        },
    ],
});
registerCommand("EDIT_GLOBAL_FILTER", {
    category: "core",
    invalidatesEvaluation: true,
});
registerCommand("REMOVE_GLOBAL_FILTER", {
    category: "core",
    invalidatesEvaluation: true,
    inverse: (cmd) => [
        {
            type: "ADD_GLOBAL_FILTER",
            filter: {},
        },
    ],
});
registerCommand("MOVE_GLOBAL_FILTER", {
    category: "core",
    inverse: (cmd) => [
        {
            type: "MOVE_GLOBAL_FILTER",
            id: cmd.id,
            delta: cmd.delta * -1,
        },
    ],
});

// `isEvaluationCommand` is needed for the local commands handled by the global
// filters, list, pivot and chart core view plugins, which are evaluation plugins.
registerCommand("SET_GLOBAL_FILTER_VALUE", {
    category: "local",
    isEvaluationCommand: true,
    invalidatesEvaluation: true,
    allowedInReadonly: true,
});
registerCommand("SET_MANY_GLOBAL_FILTER_VALUE", {
    category: "local",
    allowedInReadonly: true,
});
registerCommand("SET_DATASOURCE_FIELD_MATCHING", { category: "local" });
registerCommand("UPDATE_OBJECT_DOMAINS", {
    category: "local",
    allowedInReadonly: true,
});
// registered here, next to the other global filter commands, although they
// belong to the logging and Odoo chart plugins.
registerCommand("LOG_DATASOURCE_EXPORT", {
    category: "local",
    allowedInReadonly: true,
    allowedOnLockedSheet: true,
});
registerCommand("UPDATE_CHART_GRANULARITY", {
    category: "local",
    allowedInReadonly: true,
});

export { GlobalFiltersCorePlugin, GlobalFiltersCoreViewPlugin, GlobalFiltersUIPlugin };
