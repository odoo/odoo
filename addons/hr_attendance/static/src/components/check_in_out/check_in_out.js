import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class CheckInOut extends Component {
    static template = "hr_attendance.CheckInOut";
    static props = {
        checkedIn: Boolean,
        employeeId: Number,
        nextAction: String,
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.onClickSignInOut = useDebounced(this.signInOut, 200, { immediate: true });
    }

    async signInOut() {
        navigator.geolocation.getCurrentPosition(
            ({coords: {latitude, longitude}}) => {
                this.orm.call("hr.employee", "update_last_position", [
                    [this.props.employeeId],
                    latitude,
                    longitude
                ])
            },
            err => {
                this.orm.call("hr.employee", "update_last_position", [
                    [this.props.employeeId],
                    false,
                    false
                ])
            })
        const result = await this.orm.call("hr.employee", "attendance_manual", [
            [this.props.employeeId],
            this.props.nextAction,
        ]);
        if (result.action) {
            this.actionService.doAction(result.action);
        } else if (result.warning) {
            this.notification.add(result.warning, {type: "danger"});
        }
    }
}
