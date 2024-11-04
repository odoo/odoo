import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulate the initialization of the attendance systray data
     * @override
     */
    async _performRPC(route, args) {
        if (route === "/hr_attendance/attendance_user_data") {
            return Promise.resolve({
                "id": 1,
                "employee_name": "Mitchell Admin",
                "employee_avatar": false,
                "hours_today": 0.0019,
                "total_overtime": 0,
                "last_attendance_worked_hours": 0.0019,
                "last_check_in": "2023-10-02 07:54:31",
                "attendance_state": "checked_out",
                "hours_previously_today": 0,
                "kiosk_delay": 10000,
                "attendance": {
                    "check_in": "2023-10-02 07:54:31",
                    "check_out": "2023-10-02 07:54:38"
                },
                "overtime_today": 0,
                "use_pin": false
            })
        }
        return super._performRPC(...arguments);
    },
});
