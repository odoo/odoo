/** @odoo-module */
import { _lt } from "@web/core/l10n/translation";

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

import "./list_functions";

import ListCorePlugin from "@spreadsheet/list/plugins/list_core_plugin";
import ListUIPlugin from "@spreadsheet/list/plugins/list_ui_plugin";

import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "./list_actions";
const { inverseCommandRegistry } = spreadsheet.registries;

function identity(cmd) {
    return [cmd];
}

const { coreTypes, invalidateEvaluationCommands } = spreadsheet;
const { cellMenuRegistry } = spreadsheet.registries;

coreTypes.add("INSERT_ODOO_LIST");
coreTypes.add("RENAME_ODOO_LIST");
coreTypes.add("REMOVE_ODOO_LIST");
coreTypes.add("RE_INSERT_ODOO_LIST");
coreTypes.add("UPDATE_ODOO_LIST_DOMAIN");
coreTypes.add("ADD_LIST_DOMAIN");

invalidateEvaluationCommands.add("UPDATE_ODOO_LIST_DOMAIN");
invalidateEvaluationCommands.add("INSERT_ODOO_LIST");
invalidateEvaluationCommands.add("REMOVE_ODOO_LIST");

cellMenuRegistry.add("list_see_record", {
    name: _lt("See record"),
    sequence: 200,
    action: async (env) => {
        const cell = env.model.getters.getActiveCell();
        await SEE_RECORD_LIST(cell, env);
    },
    isVisible: (env) => {
        const cell = env.model.getters.getActiveCell();
        return SEE_RECORD_LIST_VISIBLE(cell);
    },
});

inverseCommandRegistry
    .add("INSERT_ODOO_LIST", identity)
    .add("UPDATE_ODOO_LIST_DOMAIN", identity)
    .add("RE_INSERT_ODOO_LIST", identity)
    .add("RENAME_ODOO_LIST", identity)
    .add("REMOVE_ODOO_LIST", identity);

export { ListCorePlugin, ListUIPlugin };
