import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        this.attendanceStates = {};
        this.attendanceKioskInfo = null;
        await super.setup(...arguments);
    },

    async refreshAttendanceStates() {
        const employeeIds = this.models["hr.employee"].map((employee) => employee.id);
        const states = await this.data.silentCall("hr.employee", "get_pos_attendance_states", [
            employeeIds,
        ]);
        this.attendanceStates = states || this.attendanceStates;
    },

    isEmployeeCheckedIn(employee) {
        return this.attendanceStates[employee.id] === "checked_in";
    },
});
