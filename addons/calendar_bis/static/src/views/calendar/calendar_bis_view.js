/** @odoo-module **/

import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { CalendarBisController } from "@calendar_bis/views/calendar/calendar_bis_controller";
import { CalendarBisModel } from "./calendar_bis_model";

export const calendarBisView = {
    ...calendarView,
    Controller: CalendarBisController,
    Model: CalendarBisModel,
};

registry.category("views").add("calendar_bis", calendarBisView);
