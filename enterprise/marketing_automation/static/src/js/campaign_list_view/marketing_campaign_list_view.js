/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { CampaignListController } from "./marketing_campaign_list_controller";

export const CampaignListView = {
    ...listView,
    Controller: CampaignListController,
};

registry.category("views").add("marketing_campaign_list_view", CampaignListView);
