/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

const MoveListView = {
    ...listView,
    searchMenuTypes: [],
};

registry.category("views").add('subcontracting_portal_move_list_view', MoveListView);
