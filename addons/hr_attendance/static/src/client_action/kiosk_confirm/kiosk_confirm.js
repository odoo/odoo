/** @odoo-module **/

import { CardLayout } from "@hr_attendance/components/card_layout/card_layout";
import { CheckInOut } from "@hr_attendance/components/check_in_out/check_in_out";
import { Component, onWillStart, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class KioskConfirm extends Component {
    setup() {
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.user = useService("user");

        this.padButtons = [
            ...Array.from({ length: 9 }, (_, i) => [i + 1]), // [[1], ..., [9]]
            ["C", "btn-warning"],
            [0],
            ["OK", "btn-primary"],
        ];
        this.state = useState({
            codePin: "",
        });
        this.lockPad = false;

        this.nextAction = "hr_attendance.hr_attendance_action_kiosk_mode";
        const { employee_id, employee_name, employee_state, employee_hours_today } =
            this.props.action;
        this.employeeId = employee_id;
        this.employeeName = employee_name;
        this.checkedIn = employee_state === "checked_in";
        this.employeeHoursToday = registry.category("formatters").get("float_time")(
            employee_hours_today
        );

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.use_pin = await this.user.hasGroup("hr_attendance.group_hr_attendance_use_pin");

        if (this.use_pin) {
            browser.addEventListener('keydown', async (ev) => {
                const allowedKeys = [...Array(10).keys()].reduce((acc, value) => { // { from '0': '0' ... to '9': '9' }
                    acc[value] = value;
                    return acc;
                }, {
                    'Delete': 'C',
                    'Enter': 'OK',
                    'Backspace': null,
                });
                const key = ev.key;

                if (!Object.keys(allowedKeys).includes(key)) {
                    return;
                }

                ev.preventDefault();
                ev.stopPropagation();

                if (allowedKeys[key]) {
                    await this.onClickPadButton(allowedKeys[key]);
                }
                else {
                    this.state.codePin = this.state.codePin.substring(0, this.state.codePin.length - 1);
                }
            });
        }
    }

    onClickBack() {
        this.actionService.doAction(this.nextAction, { clearBreadcrumbs: true });
    }

    async onClickPadButton(value) {
        if (this.lockPad) {
            return;
        }

        if (value === "C") {
            this.state.codePin = "";
        } else if (value === "OK") {
            this.lockPad = true;
            const result = await this.orm.call("hr.employee", "attendance_manual", [
                [this.employeeId],
                this.nextAction,
                this.state.codePin,
            ]);
            if (result.action) {
                this.actionService.doAction(result.action);
            } else if (result.warning) {
                this.notification.add(result.warning, { type: "danger" });
                this.state.codePin = "";
                browser.setTimeout(() => {
                    this.lockPad = false;
                }, 500);
            }
        } else {
            this.state.codePin += value;
        }
    }
}

KioskConfirm.template = "hr_attendance.KioskConfirm";
KioskConfirm.components = { CardLayout, CheckInOut };

registry.category("actions").add("hr_attendance_kiosk_confirm", KioskConfirm);
