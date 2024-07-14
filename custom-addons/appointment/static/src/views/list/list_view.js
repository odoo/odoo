/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { AppointmentBookingListRenderer } from "@appointment/views/list/list_renderer";

export const AppointmentBookingListView = {
    ...listView,
    Renderer: AppointmentBookingListRenderer,
};

registry.category("views").add("appointment_booking_list", AppointmentBookingListView);
