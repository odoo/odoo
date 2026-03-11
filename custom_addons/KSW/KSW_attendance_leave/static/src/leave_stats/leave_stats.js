/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { LeaveStatsComponent, leaveStatsComponent } from "@hr_holidays/leave_stats/leave_stats";

// Add state and x_attendance_ids to field dependencies so the observer fires on changes
leaveStatsComponent.fieldDependencies.push(
    { name: "state", type: "selection" },
    { name: "x_attendance_count", type: "integer" },
);

patch(LeaveStatsComponent.prototype, {
    setup() {
        super.setup();
        // Track state and attendance count to detect changes
        this._lastState = this.props.record.data.state;
        this._lastAttCount = this.props.record.data.x_attendance_count || 0;

        useRecordObserver(async (record) => {
            const newState = record.data.state;
            const newAttCount = record.data.x_attendance_count || 0;
            const changed = newState !== this._lastState || newAttCount !== this._lastAttCount;
            this._lastState = newState;
            this._lastAttCount = newAttCount;
            if (changed) {
                const employee = record.data.employee_id;
                const department = record.data.department_id;
                const proms = [];
                if (employee) {
                    proms.push(this.loadLeaves(employee));
                }
                if (department && employee) {
                    proms.push(this.loadDepartmentLeaves(department, employee));
                }
                await Promise.all(proms);
            }
        });
    },

    async loadLeaves(employee) {
        await super.loadLeaves(employee);
        await this._loadAttendanceBreakdown(this.state.leaves);
    },

    async loadDepartmentLeaves(department, employee) {
        await super.loadDepartmentLeaves(department, employee);
        await this._loadAttendanceBreakdown(this.state.departmentLeaves);
    },

    async _loadAttendanceBreakdown(leaves) {
        if (!leaves.length) return;
        const ids = leaves.map((l) => l.id);
        const counts = await this.orm.read("hr.leave", ids, ["x_attendance_count"]);
        const countMap = Object.fromEntries(
            counts.map((c) => [c.id, c.x_attendance_count])
        );
        leaves.forEach((l) => {
            l.x_attendance_count = countMap[l.id] || 0;
            l.attendance_breakdown = [];
        });
        const idsWithAttendance = leaves
            .filter((l) => l.x_attendance_count > 0)
            .map((l) => l.id);
        if (idsWithAttendance.length) {
            const breakdown = await this.orm.call(
                "hr.leave",
                "get_attendance_breakdown",
                [idsWithAttendance]
            );
            leaves.forEach((l) => {
                l.attendance_breakdown = breakdown[l.id] || [];
            });
        }
    },
});


