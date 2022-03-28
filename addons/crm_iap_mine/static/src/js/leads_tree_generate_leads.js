
/** @odoo-module **/

import { CRMKanbanView } from "@crm/js/crm_kanban";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListView } from "@web/views/list/list_view";

const { onWillStart } = owl;

export class LeadMiningRequestListView extends ListView {
    setup() {
        super.setup();

        onWillStart(async () => {
            this.isSaleManager = await this.userService.hasGroup("sales_team.group_sale_manager");
        });
    }

    onGenerateLeads() {
        const { default_type } = this.model.root.context;
        this.actionService.doAction({
            name: "Generate Leads",
            type: "ir.actions.act_window",
            res_model: "crm.iap.lead.mining.request",
            target: "new",
            views: [[false, "form"]],
            context: { is_modal: true, default_lead_type: default_type },
        });
    }
}

LeadMiningRequestListView.buttonTemplate = "crm_iap_mine.ListView.Buttons";

export class LeadMiningRequestKanbanView extends CRMKanbanView {
    setup() {
        super.setup();

        this.userService = useService("user");
        onWillStart(async () => {
            this.isSaleManager = await this.userService.hasGroup("sales_team.group_sale_manager");
        });
    }

    onGenerateLeads() {
        const { default_type } = this.model.root.context;
        this.actionService.doAction({
            name: "Generate Leads",
            type: "ir.actions.act_window",
            res_model: "crm.iap.lead.mining.request",
            target: "new",
            views: [[false, "form"]],
            context: { is_modal: true, default_lead_type: default_type },
        });
    }
}

LeadMiningRequestKanbanView.buttonTemplate = "crm_iap_mine.KanbanView.Buttons";

registry
    .category("views")
    .add("crm_iap_lead_mining_request_tree", LeadMiningRequestListView)
    .add("crm_iap_lead_mining_request_kanban", LeadMiningRequestKanbanView);
