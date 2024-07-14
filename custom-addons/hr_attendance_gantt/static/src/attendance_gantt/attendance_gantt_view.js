/* @odoo-module */

import { ganttView } from "@web_gantt/gantt_view";
import { registry } from "@web/core/registry";
import {AttendanceGanttModel} from "./attendance_gantt_model";
import {AttendanceGanttRenderer} from "./attendance_gantt_renderer";

const viewRegistry = registry.category("views");

export const attendanceGanttView = {
    ...ganttView,
    Model: AttendanceGanttModel,
    Renderer: AttendanceGanttRenderer
};

viewRegistry.add("attendance_gantt", attendanceGanttView);
