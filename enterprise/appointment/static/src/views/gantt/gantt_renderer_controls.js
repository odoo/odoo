import { GanttRendererControls } from "@web_gantt/gantt_renderer_controls";

export class AppointmentBookingGanttRendererControls extends GanttRendererControls {
    static template = "appointment.AppointmentBookingGanttRendererControls";
    static props = [...GanttRendererControls.props, "onClickAddLeave", "showAddLeaveButton"];
}
