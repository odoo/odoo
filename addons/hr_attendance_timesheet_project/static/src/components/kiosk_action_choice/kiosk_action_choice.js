/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class KioskActionChoice extends Component {
    static template = "hr_attendance_timesheet_project.KioskActionChoice";
    static props = {
        employeeId: Number,
        attendanceId: Number,
        currentProjectName: { type: String, optional: true },
        onCheckOut: Function,
        onProjectChanged: Function,
        onCancel: { type: Function, optional: true },
        close: Function,  // Required prop from dialog service
    };

    setup() {
        this.state = useState({
            showProjectList: false,
            projects: [],
            loading: false,
            selectedProjectId: null,
            error: null,
        });

        console.log("[KioskActionChoice] Component setup with props:", this.props);
    }

    async onClickChangeProject() {
        console.log("[KioskActionChoice] Change project button clicked");
        // Expand to show project list
        this.state.loading = true;
        this.state.error = null;

        try {
            const result = await rpc("/hr_attendance/kiosk_get_employee_projects", {
                employee_id: this.props.employeeId,
            });

            console.log("[KioskActionChoice] Projects loaded:", result);

            this.state.projects = result.projects || [];
            this.state.showProjectList = true;

            if (this.state.projects.length === 0) {
                this.state.error = "No projects available";
                console.warn("[KioskActionChoice] No projects found");
            }
        } catch (error) {
            console.error("[KioskActionChoice] Failed to load projects:", error);
            this.state.error = "Failed to load projects. Please try again.";
        } finally {
            this.state.loading = false;
        }
    }

    async onSelectProject(projectId) {
        console.log("[KioskActionChoice] Project selected:", projectId);

        this.state.selectedProjectId = projectId;
        this.state.loading = true;
        this.state.error = null;

        try {
            const result = await rpc("/hr_attendance/kiosk_change_project", {
                attendance_id: this.props.attendanceId,
                project_id: projectId,
            });

            console.log("[KioskActionChoice] Project change result:", result);

            if (result.success === false) {
                throw new Error(result.error || "Failed to change project");
            }

            // Close dialog first
            if (this.props.close) {
                this.props.close();
            }

            // Notify parent component of success
            await this.props.onProjectChanged(projectId);
        } catch (error) {
            console.error("[KioskActionChoice] Failed to change project:", error);
            this.state.error = error.message || "Failed to change project. Please try again.";
        } finally {
            this.state.loading = false;
        }
    }

    async onClickCheckOut() {
        console.log("[KioskActionChoice] Check out button clicked");

        this.state.loading = true;
        this.state.error = null;

        try {
            // Close dialog first
            if (this.props.close) {
                this.props.close();
            }

            // Call parent's check-out handler
            await this.props.onCheckOut();
        } catch (error) {
            console.error("[KioskActionChoice] Check out error:", error);
            this.state.error = "Failed to check out. Please try again.";
            this.state.loading = false;
        }
    }

    onClickCancel() {
        console.log("[KioskActionChoice] Cancel button clicked");

        // Close dialog
        if (this.props.close) {
            this.props.close();
        }

        // Call cancel handler if provided
        if (this.props.onCancel) {
            this.props.onCancel();
        }
    }

    onClickBack() {
        console.log("[KioskActionChoice] Back button clicked");
        this.state.showProjectList = false;
        this.state.error = null;
        this.state.selectedProjectId = null;
    }
}
