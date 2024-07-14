/** @odoo-module **/

import { registry } from "@web/core/registry";
import { AppointmentBookingGanttController } from "@appointment/views/gantt/gantt_controller";
import { AppointmentBookingGanttModel } from "@appointment/views/gantt/gantt_model";
import { AppointmentBookingGanttRenderer } from "@appointment/views/gantt/gantt_renderer";
import { ganttView } from "@web_gantt/gantt_view";

export const AppointmentBookingGanttView = {
    ...ganttView,
    Controller: AppointmentBookingGanttController,
    Model: AppointmentBookingGanttModel,
    Renderer: AppointmentBookingGanttRenderer,
};

registry.category("views").add("appointment_booking_gantt", AppointmentBookingGanttView);
