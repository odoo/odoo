/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

import { useChildSubEnv } from "@odoo/owl";

export class BankRecListController extends ListController {

    setup() {
        super.setup(...arguments);

        this.skipKanbanRestore = {};

        useChildSubEnv({
            skipKanbanRestoreNeeded: (stLineId) => this.skipKanbanRestore[stLineId],
        });
    }

    /**
      * Override
      * Don't allow bank_rec_form to be restored with previous values since the statement line has changed.
      */
    async onRecordSaved(record) {
        this.skipKanbanRestore[record.resId] = true;
        return super.onRecordSaved(...arguments);
    }

}

export const bankRecListView = {
    ...listView,
    Controller: BankRecListController,
}

registry.category("views").add("bank_rec_list", bankRecListView);
