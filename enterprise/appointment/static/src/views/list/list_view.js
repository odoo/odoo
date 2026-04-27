/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { AppointmentBookingListRenderer, AppointmentTypeListRenderer} from "@appointment/views/list/list_renderer";

export const AppointmentBookingListView = {
    ...listView,
    Renderer: AppointmentBookingListRenderer,
};

registry.category("views").add("appointment_booking_list", AppointmentBookingListView);

export const AppointmentTypeListView = {
    ...listView,
    Renderer: AppointmentTypeListRenderer,
};

registry.category("views").add("appointment_type_list", AppointmentTypeListView);
