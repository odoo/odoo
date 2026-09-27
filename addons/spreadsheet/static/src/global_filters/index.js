import * as spreadsheet from "@odoo/o-spreadsheet";

import { GlobalFiltersUIPlugin } from "./plugins/global_filters_ui_plugin";
import { GlobalFiltersCorePlugin } from "./plugins/global_filters_core_plugin";
import { GlobalFiltersCoreViewPlugin } from "./plugins/global_filters_core_view_plugin";
const { inverseCommandRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

const {
    coreTypes,
    evaluationCommandTypes,
    invalidateEvaluationCommands,
    readonlyAllowedCommands,
    lockedSheetAllowedCommands,
} = spreadsheet;

coreTypes.add("ADD_GLOBAL_FILTER");
coreTypes.add("EDIT_GLOBAL_FILTER");
coreTypes.add("REMOVE_GLOBAL_FILTER");
coreTypes.add("MOVE_GLOBAL_FILTER");

// `evaluationCommandTypes` is a snapshot of `coreTypes` taken when o-spreadsheet
// is loaded, so every core type added here has to be registered again for
// evaluation plugins to receive it.
// TODO: remove once `isEvaluationCommand` also checks `coreTypes` at call time.
evaluationCommandTypes.add("ADD_GLOBAL_FILTER");
evaluationCommandTypes.add("EDIT_GLOBAL_FILTER");
evaluationCommandTypes.add("REMOVE_GLOBAL_FILTER");
evaluationCommandTypes.add("MOVE_GLOBAL_FILTER");
// local command handled by the global filters, list, pivot and chart core view plugins
evaluationCommandTypes.add("SET_GLOBAL_FILTER_VALUE");

invalidateEvaluationCommands.add("ADD_GLOBAL_FILTER");
invalidateEvaluationCommands.add("EDIT_GLOBAL_FILTER");
invalidateEvaluationCommands.add("REMOVE_GLOBAL_FILTER");
invalidateEvaluationCommands.add("SET_GLOBAL_FILTER_VALUE");

readonlyAllowedCommands.add("SET_GLOBAL_FILTER_VALUE");
readonlyAllowedCommands.add("SET_MANY_GLOBAL_FILTER_VALUE");
readonlyAllowedCommands.add("UPDATE_OBJECT_DOMAINS");
readonlyAllowedCommands.add("LOG_DATASOURCE_EXPORT");

readonlyAllowedCommands.add("UPDATE_CHART_GRANULARITY");

lockedSheetAllowedCommands.add("LOG_DATASOURCE_EXPORT");

inverseCommandRegistry
    .add("EDIT_GLOBAL_FILTER", identity)
    .add("ADD_GLOBAL_FILTER", (cmd) => [
        {
            type: "REMOVE_GLOBAL_FILTER",
            id: cmd.filter.id,
        },
    ])
    .add("REMOVE_GLOBAL_FILTER", (cmd) => [
        {
            type: "ADD_GLOBAL_FILTER",
            filter: {},
        },
    ])
    .add("MOVE_GLOBAL_FILTER", (cmd) => [
        {
            type: "MOVE_GLOBAL_FILTER",
            id: cmd.id,
            delta: cmd.delta * -1,
        },
    ]);

export { GlobalFiltersCorePlugin, GlobalFiltersCoreViewPlugin, GlobalFiltersUIPlugin };
