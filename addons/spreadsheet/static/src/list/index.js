import { _t } from "@web/core/l10n/translation";

import * as spreadsheet from "@odoo/o-spreadsheet";

import "./list_functions";

import { ListCorePlugin } from "@spreadsheet/list/plugins/list_core_plugin";
import { ListCoreViewPlugin } from "@spreadsheet/list/plugins/list_core_view_plugin";
import { ListUIPlugin } from "@spreadsheet/list/plugins/list_ui_plugin";

import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "./list_actions";
const { registerCommand } = spreadsheet;

registerCommand("INSERT_ODOO_LIST", { category: "core", invalidatesEvaluation: true });
registerCommand("RENAME_ODOO_LIST", { category: "core" });
registerCommand("REMOVE_ODOO_LIST", { category: "core", invalidatesEvaluation: true });
registerCommand("RE_INSERT_ODOO_LIST", { category: "core" });
registerCommand("UPDATE_ODOO_LIST_DOMAIN", { category: "core", invalidatesEvaluation: true });
registerCommand("UPDATE_ODOO_LIST", { category: "core", invalidatesEvaluation: true });
registerCommand("ADD_LIST_DOMAIN", { category: "core" });
registerCommand("DUPLICATE_ODOO_LIST", { category: "core" });

// Local commands handled by the list UI plugin.
registerCommand("INSERT_ODOO_LIST_WITH_TABLE", { category: "local" });
registerCommand("RE_INSERT_ODOO_LIST_WITH_TABLE", { category: "local" });
registerCommand("INSERT_NEW_ODOO_LIST", { category: "local" });
registerCommand("DUPLICATE_ODOO_LIST_IN_NEW_SHEET", { category: "local" });

const { cellMenuRegistry } = spreadsheet.registries;

cellMenuRegistry.add(
    "list_see_record",
    /** @type {import("@odoo/o-spreadsheet").ActionSpec}*/ ({
        name: _t("See record"),
        sequence: 200,
        execute: async (env, isMiddleClick) => {
            const position = env.model.getters.getActivePosition();
            await SEE_RECORD_LIST(position, env, isMiddleClick);
        },
        isVisible: (env) => {
            const position = env.model.getters.getActivePosition();
            return SEE_RECORD_LIST_VISIBLE(position, env.model.getters);
        },
        icon: "o-spreadsheet-Icon.SEE_RECORDS",
    })
);

export { ListCorePlugin, ListCoreViewPlugin, ListUIPlugin };
