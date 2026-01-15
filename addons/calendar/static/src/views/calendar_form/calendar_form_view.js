import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { CalendarFormController } from "@calendar/views/calendar_form/calendar_form_controller";
import { CalendarFormModel } from "@calendar/views/calendar_form/calendar_form_model";

export const CalendarFormView = {
    ...formView,
    Controller: CalendarFormController,
    Model: CalendarFormModel,
};

registry.category("views").add("calendar_form", CalendarFormView);
