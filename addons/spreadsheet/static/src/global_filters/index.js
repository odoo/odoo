import * as spreadsheet from "@odoo/o-spreadsheet";

import { GlobalFiltersUIPlugin } from "./plugins/global_filters_ui_plugin";
import { GlobalFiltersCorePlugin } from "./plugins/global_filters_core_plugin";
import { GlobalFiltersCoreViewPlugin } from "./plugins/global_filters_core_view_plugin";
const { inverseCommandRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

const { coreTypes, invalidateEvaluationCommands, readonlyAllowedCommands } = spreadsheet;

coreTypes.add("ADD_GLOBAL_FILTER");
coreTypes.add("EDIT_GLOBAL_FILTER");
coreTypes.add("REMOVE_GLOBAL_FILTER");
coreTypes.add("MOVE_GLOBAL_FILTER");

invalidateEvaluationCommands.add("ADD_GLOBAL_FILTER");
invalidateEvaluationCommands.add("EDIT_GLOBAL_FILTER");
invalidateEvaluationCommands.add("REMOVE_GLOBAL_FILTER");
invalidateEvaluationCommands.add("SET_GLOBAL_FILTER_VALUE");

readonlyAllowedCommands.add("SET_GLOBAL_FILTER_VALUE");
readonlyAllowedCommands.add("SET_MANY_GLOBAL_FILTER_VALUE");
readonlyAllowedCommands.add("UPDATE_OBJECT_DOMAINS");
<<<<<<< fbc9a7b4b55c24a84a792be9ced7fc3af4a17c34
readonlyAllowedCommands.add("LOG_DATASOURCE_EXPORT");

readonlyAllowedCommands.add("UPDATE_CHART_GRANULARITY");
||||||| b026f26a46ff36b5d405a559d5e0b11589dad1da
=======
readonlyAllowedCommands.add("LOG_DATASOURCE_EXPORT");
>>>>>>> 69e2c0070ced7f95e595348bb139ac476bc0a579

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
