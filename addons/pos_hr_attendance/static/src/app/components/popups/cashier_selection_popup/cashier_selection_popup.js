import { patch } from "@web/core/utils/patch";
import { CashierSelectionPopup } from "@pos_hr/app/components/popups/cashier_selection_popup/cashier_selection_popup";

patch(CashierSelectionPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.attendanceStates = {};
        this.loadAttendanceStates();
    },

    async loadAttendanceStates() {
        const employeeIds = this.props.employees.map((employee) => employee.id);
        if (this.props.currentCashier) {
            employeeIds.push(this.props.currentCashier.id);
        }
        const states = await this.pos.data.silentCall("hr.employee", "get_pos_attendance_states", [
            employeeIds,
        ]);
        this.state.attendanceStates = states || {};
    },

    isEmployeeCheckedIn(employee) {
        return this.state.attendanceStates[employee.id] === "checked_in";
    },
});
