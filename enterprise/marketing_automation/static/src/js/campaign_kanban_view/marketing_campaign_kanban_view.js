/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { CampaignKanbanController } from "./marketing_campaign_kanban_controller";

export const CampaignKanbanView = {
    ...kanbanView,
    Controller: CampaignKanbanController,
};

registry.category("views").add("marketing_campaign_kanban_view", CampaignKanbanView);
