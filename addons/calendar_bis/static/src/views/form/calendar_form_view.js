/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { CalendarFormController } from "@calendar_bis/views/form/calendar_form_controller";

export const CalendarFormView = {
    ...formView,
    Controller: CalendarFormController,
};

registry.category("views").add("calendar_bis_form", CalendarFormView);
