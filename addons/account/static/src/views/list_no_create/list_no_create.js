/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

export class ListNoCreateController extends ListController {
    setup() {
        super.setup();
        // Explicitly hide the "New" button from the list UI
        this.activeActions.create = false;
    }
}

export const listNoCreateView = {
    ...listView,
    Controller: ListNoCreateController,
};

registry.category("views").add("list_no_create", listNoCreateView);
