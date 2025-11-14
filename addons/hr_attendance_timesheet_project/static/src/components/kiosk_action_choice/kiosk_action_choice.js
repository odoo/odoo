/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";

export class KioskActionChoice extends Component {
    static template = "hr_attendance_timesheet_project.KioskActionChoice";
    static components = { Dialog };
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
            closing: false,
            searchTerm: '',
        });

        console.log("[KioskActionChoice] Component setup with props:", this.props);
    }

    get filteredProjects() {
        if (!this.state.searchTerm || !this.state.searchTerm.trim()) {
            return this.state.projects;
        }

        const searchLower = this.state.searchTerm.toLowerCase().trim();
        return this.state.projects.filter(project => {
            const projectNameMatch = project.name.toLowerCase().includes(searchLower);
            const partnerNameMatch = project.partner_name && project.partner_name.toLowerCase().includes(searchLower);
            return projectNameMatch || partnerNameMatch;
        });
    }

    async onClickChangeProject() {
        console.log("[KioskActionChoice] Change project button clicked");
        // Expand to show project list
        this.state.loading = true;
        this.state.error = null;
        this.state.showProjectList = true;

        try {
            const result = await rpc("/hr_attendance/kiosk_get_employee_projects", {
                employee_id: this.props.employeeId,
            });

            console.log("[KioskActionChoice] Projects loaded:", result);

            this.state.projects = result.projects || [];

            if (this.state.projects.length === 0) {
                this.state.error = "No projects available";
                console.warn("[KioskActionChoice] No projects found");
            }
        } catch (error) {
            console.error("[KioskActionChoice] Failed to load projects:", error);
            this.state.error = "Failed to load projects. Please try again.";
            this.state.projects = []; // Ensure it's always an array
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

            // Notify parent component of success first
            await this.props.onProjectChanged(projectId);

            // Set closing flag to prevent further renders
            this.state.closing = true;

            // Close dialog last to avoid re-render issues
            if (this.props.close) {
                this.props.close();
            }
        } catch (error) {
            console.error("[KioskActionChoice] Failed to change project:", error);
            this.state.error = error.message || "Failed to change project. Please try again.";
            this.state.loading = false;
        }
    }

    async onClickCheckOut() {
        console.log("[KioskActionChoice] Check out button clicked");

        this.state.loading = true;
        this.state.error = null;

        try {
            // Call parent's check-out handler first
            await this.props.onCheckOut();

            // Set closing flag to prevent further renders
            this.state.closing = true;

            // Close dialog last
            if (this.props.close) {
                this.props.close();
            }
        } catch (error) {
            console.error("[KioskActionChoice] Check out error:", error);
            this.state.error = "Failed to check out. Please try again.";
            this.state.loading = false;
        }
    }

    onClickCancel() {
        console.log("[KioskActionChoice] Cancel button clicked");

        // Set closing flag to prevent further renders
        this.state.closing = true;

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
        this.state.searchTerm = '';
    }

    onSearchInput(event) {
        this.state.searchTerm = event.target.value;
    }

    clearSearch() {
        this.state.searchTerm = '';
    }
}
