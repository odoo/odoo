/** odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { CampaignFormController } from "./marketing_campaign_form_controller";

export const CampaignFormView = {
    ...formView,
    Controller: CampaignFormController,
};

registry.category("views").add("marketing_campaign_form_view", CampaignFormView);
