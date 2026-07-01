import { activityView } from "@mail/views/web/activity/activity_view";
import { CrmControlPanel } from "@crm/views/crm_control_panel/crm_control_panel";
import { CrmSearchModel } from "@crm/views/crm_search_model";
import { registry } from "@web/core/registry";

export const crmActivityView = {
    ...activityView,
    ControlPanel: CrmControlPanel,
    SearchModel: CrmSearchModel,
};

registry.category("views").add("crm_activity", crmActivityView);
