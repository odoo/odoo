/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { KioskActionChoice } from "@hr_attendance_timesheet_project/components/kiosk_action_choice/kiosk_action_choice";
import { rpc } from "@web/core/network/rpc";
import { isIosApp } from "@web/core/browser/feature_detection";

patch(ActivityMenu.prototype, {
    async signInOut() {
        this.dropdown.close();

        // If checking out (currently checked in), show dialog
        if (this.state.checkedIn) {
            await this.showCheckOutDialog();
            return;
        }

        // Otherwise, check in directly (call parent implementation)
        return super.signInOut();
    },

    async showCheckOutDialog() {
        try {
            // Get current attendance record
            const attendanceRecords = await this.orm.searchRead(
                'hr.attendance',
                [['employee_id', '=', this.employee.id], ['check_out', '=', false]],
                ['id', 'current_project_id'],
                { limit: 1 }
            );

            if (!attendanceRecords || attendanceRecords.length === 0) {
                console.warn("[ActivityMenu] No active attendance found");
                // Fallback to direct check-out
                await this.handleCheckOut();
                return;
            }

            const attendance = attendanceRecords[0];
            const currentProjectName = attendance.current_project_id ? attendance.current_project_id[1] : null;

            // Show the dialog
            this.dialog.add(KioskActionChoice, {
                employeeId: this.employee.id,
                attendanceId: attendance.id,
                currentProjectName: currentProjectName,
                onCheckOut: async () => {
                    await this.handleCheckOut();
                },
                onProjectChanged: async (projectId) => {
                    await this.handleProjectChanged(projectId);
                },
                onCancel: () => {
                    // Do nothing, just close the dialog
                },
            });
        } catch (error) {
            console.error("[ActivityMenu] Error showing check-out dialog:", error);
            // Fallback to direct check-out
            await this.handleCheckOut();
        }
    },

    async handleCheckOut() {
        // Perform check-out with geolocation if enabled
        const trackingEnabled = this.employee && this.employee.device_tracking_enabled;
        if (trackingEnabled && !isIosApp() && navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                async ({coords: {latitude, longitude}}) => {
                    this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                        latitude,
                        longitude
                    })
                    this._searchReadEmployeeFill();
                },
                async err => {
                    this.employee = await rpc("/hr_attendance/systray_check_in_out")
                    this._searchReadEmployeeFill();
                },
                {
                    enableHighAccuracy: true,
                }
            )
        } else {
            this.employee = await rpc("/hr_attendance/systray_check_in_out")
            this._searchReadEmployeeFill();
        }
    },

    async handleProjectChanged(projectId) {
        // Just refresh employee data to reflect the project change
        await this.searchReadEmployee();
    },
});
