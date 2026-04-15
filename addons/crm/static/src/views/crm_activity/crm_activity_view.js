import { activityView } from "@mail/views/web/activity/activity_view";
import { CrmSearchModel } from "@crm/views/crm_search_model";
import { registry } from "@web/core/registry";

export const crmActivityView = {
    ...activityView,
    SearchModel: CrmSearchModel,
}

registry.category("views").add("crm_activity", crmActivityView);
