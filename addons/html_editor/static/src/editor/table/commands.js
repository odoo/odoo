/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("powerbox_commands").add("table", {
    name: _t("Table"),
    description: _t("Insert a table"),
    category: "structure",
    fontawesome: "fa-table",
    action(dispatch) {
        dispatch("OPEN_TABLE_PICKER");
    },
});
