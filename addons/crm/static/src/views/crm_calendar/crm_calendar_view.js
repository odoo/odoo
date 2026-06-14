import { calendarView } from "@web/views/calendar/calendar_view";
import { CrmSearchModel } from "@crm/views/crm_search_model";
import { registry } from "@web/core/registry";

export const crmCalendarView = {
    ...calendarView,
    SearchModel: CrmSearchModel,
};
registry.category("views").add("crm_calendar", crmCalendarView);
