/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { useGenerateLeadsButton } from "@crm_iap_mine/views/generate_leads_hook";
import { crmKanbanView } from "@crm/views/crm_kanban/crm_kanban_view";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class LeadMiningRequestListController extends ListController {
    setup() {
        super.setup();
        useGenerateLeadsButton();
    }
}

registry.category("views").add("crm_iap_lead_mining_request_tree", {
    ...listView,
    Controller: LeadMiningRequestListController,
    buttonTemplate: "LeadMiningRequestListView.buttons",
});

patch(crmKanbanView.Controller.prototype, "crm_iap_lead_mining_request_kanban", {
    setup() {
        this._super(...arguments);
        useGenerateLeadsButton();
    },
});
crmKanbanView.buttonTemplate = "LeadMiningRequestKanbanView.buttons";
