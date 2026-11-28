

/** @odoo-module **/

import { registry } from "@web/core/registry";

import { AttendanceSheet } from "../attendance_sheet/attendance_sheet";

// Keep the existing Attendance action URL, but use the same canonical
// Student Attendance screen as the direct menu action.  This
// prevents two different attendance UIs from being maintained.
registry.category("actions").add("university_attendance_reports", AttendanceSheet);
