/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

export const todoListView = {
    ...listView,
    props: (genericProps, view) => {
        const viewProps = listView.props(genericProps,view);
        viewProps.info.actionMenus.action = [];
        viewProps.info.actionMenus.print = [];
        return viewProps;
    },
};

registry.category("views").add("todo_list", todoListView);
