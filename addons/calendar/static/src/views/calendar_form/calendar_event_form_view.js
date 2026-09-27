import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { CalendarEventFormController } from "@calendar/views/calendar_form/calendar_event_form_controller";
import { CalendarEventFormModel } from "./calendar_event_form_model";


export const CalendarEventFormView = {
    ...formView,
    Controller: CalendarEventFormController,
    Model: CalendarEventFormModel,
};

registry.category("views").add("calendar_event_form", CalendarEventFormView);
