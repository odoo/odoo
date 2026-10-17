/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

export const importOnlyListView = {
    ...listView,
    buttonTemplate: "hr.NoNewListButton",
};

registry.category("views").add("no_new_list", importOnlyListView);