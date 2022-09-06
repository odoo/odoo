/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import "@spreadsheet/pivot"; // filter depends on pivot and lists for its getters
import "@spreadsheet/list"; // filter depends on pivot and lists for its getters
import FiltersEvaluationPlugin from "./plugins/filters_evaluation_plugin";
import FiltersPlugin from "./plugins/filters_plugin";
const { inverseCommandRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

const { coreTypes, invalidateEvaluationCommands, readonlyAllowedCommands } = spreadsheet;
const { corePluginRegistry, uiPluginRegistry } = spreadsheet.registries;

corePluginRegistry.add("odooFiltersPlugin", FiltersPlugin);
uiPluginRegistry.add("odooFiltersEvaluationPlugin", FiltersEvaluationPlugin);

coreTypes.add("ADD_GLOBAL_FILTER");
coreTypes.add("EDIT_GLOBAL_FILTER");
coreTypes.add("REMOVE_GLOBAL_FILTER");

invalidateEvaluationCommands.add("ADD_GLOBAL_FILTER");
invalidateEvaluationCommands.add("EDIT_GLOBAL_FILTER");
invalidateEvaluationCommands.add("REMOVE_GLOBAL_FILTER");
invalidateEvaluationCommands.add("SET_GLOBAL_FILTER_VALUE");
invalidateEvaluationCommands.add("CLEAR_GLOBAL_FILTER_VALUE");

readonlyAllowedCommands.add("SET_GLOBAL_FILTER_VALUE");
readonlyAllowedCommands.add("SET_MANY_GLOBAL_FILTER_VALUE");
readonlyAllowedCommands.add("CLEAR_GLOBAL_FILTER_VALUE");

inverseCommandRegistry
    .add("EDIT_GLOBAL_FILTER", identity)
    .add("ADD_GLOBAL_FILTER", (cmd) => {
        return [
            {
                type: "REMOVE_GLOBAL_FILTER",
                id: cmd.id,
            },
        ];
    })
    .add("REMOVE_GLOBAL_FILTER", (cmd) => {
        return [
            {
                type: "ADD_GLOBAL_FILTER",
                id: cmd.id,
                filter: {},
            },
        ];
    });
