/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";

import { GlobalFiltersUIPlugin } from "./plugins/global_filters_ui_plugin";
import { GlobalFiltersCorePlugin } from "./plugins/global_filters_core_plugin";
const { inverseCommandRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

const {
    coreTypes,
    invalidateEvaluationCommands,
    invalidateCFEvaluationCommands,
    invalidateDependenciesCommands,
    readonlyAllowedCommands,
} = spreadsheet;

coreTypes.add("ADD_GLOBAL_FILTER");
coreTypes.add("EDIT_GLOBAL_FILTER");
coreTypes.add("REMOVE_GLOBAL_FILTER");
coreTypes.add("MOVE_GLOBAL_FILTER");

invalidateEvaluationCommands.add("ADD_GLOBAL_FILTER");
invalidateEvaluationCommands.add("EDIT_GLOBAL_FILTER");
invalidateEvaluationCommands.add("REMOVE_GLOBAL_FILTER");
invalidateEvaluationCommands.add("SET_GLOBAL_FILTER_VALUE");
invalidateEvaluationCommands.add("CLEAR_GLOBAL_FILTER_VALUE");

invalidateDependenciesCommands.add("ADD_GLOBAL_FILTER");
invalidateDependenciesCommands.add("EDIT_GLOBAL_FILTER");
invalidateDependenciesCommands.add("REMOVE_GLOBAL_FILTER");
invalidateDependenciesCommands.add("SET_GLOBAL_FILTER_VALUE");
invalidateDependenciesCommands.add("CLEAR_GLOBAL_FILTER_VALUE");

invalidateCFEvaluationCommands.add("ADD_GLOBAL_FILTER");
invalidateCFEvaluationCommands.add("EDIT_GLOBAL_FILTER");
invalidateCFEvaluationCommands.add("REMOVE_GLOBAL_FILTER");
invalidateCFEvaluationCommands.add("SET_GLOBAL_FILTER_VALUE");
invalidateCFEvaluationCommands.add("CLEAR_GLOBAL_FILTER_VALUE");

readonlyAllowedCommands.add("SET_GLOBAL_FILTER_VALUE");
readonlyAllowedCommands.add("SET_MANY_GLOBAL_FILTER_VALUE");
readonlyAllowedCommands.add("CLEAR_GLOBAL_FILTER_VALUE");
readonlyAllowedCommands.add("UPDATE_OBJECT_DOMAINS");

inverseCommandRegistry
    .add("EDIT_GLOBAL_FILTER", identity)
    .add("ADD_GLOBAL_FILTER", (cmd) => {
        return [
            {
                type: "REMOVE_GLOBAL_FILTER",
                id: cmd.filter.id,
            },
        ];
    })
    .add("REMOVE_GLOBAL_FILTER", (cmd) => {
        return [
            {
                type: "ADD_GLOBAL_FILTER",
                filter: {},
            },
        ];
    });

export { GlobalFiltersCorePlugin, GlobalFiltersUIPlugin };
