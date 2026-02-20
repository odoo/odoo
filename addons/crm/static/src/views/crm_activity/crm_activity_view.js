import { activityView } from "@mail/views/web/activity/activity_view";
import { CrmControlPanel } from "@crm/views/crm_control_panel/crm_control_panel";
import { CrmActivityModel } from "@crm/views/crm_activity/crm_activity_model";
import { registry } from "@web/core/registry";

export const crmActivityView = {
    ...activityView,
    ControlPanel: CrmControlPanel,
    Model: CrmActivityModel,
}

registry.category("views").add("crm_activity", crmActivityView);
