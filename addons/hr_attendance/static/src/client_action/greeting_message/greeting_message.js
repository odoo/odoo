/** @odoo-module **/

import { CardLayout } from "@hr_attendance/components/card_layout/card_layout";
import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";

const { Duration } = luxon;

export class GreetingMessage extends Component {
    setup() {
        const { action } = this.props;

        this.actionService = useService("action");
        this.notificationService = useService("notification");
        this.orm = useService("orm");
        this.user = useService("user");

        this.kioskDelay = action.kiosk_delay;
        this.state = useState({
            message: "",
            randomMessage: "",
            showWarningMessage: false,
        });

        onWillStart(this.onWillStart);
        onWillUnmount(() => this.return_to_main_menu && clearTimeout(this.return_to_main_menu));

        let activeBarcode = true;
        if (!this.props.action.attendance) {
            activeBarcode = false;
            return;
        }

        this.next_action =
            action.next_action || "hr_attendance.hr_attendance_action_my_attendances";
        // no listening to barcode scans if we aren't coming from the kiosk mode (and thus not going back to it with next_action)
        if (
            this.next_action !== "hr_attendance.hr_attendance_action_kiosk_mode" &&
            this.next_action.tag !== "hr_attendance_kiosk_mode"
        ) {
            activeBarcode = false;
        }

        this.attendance = action.attendance;
        // We receive the check in/out times in UTC
        // This widget only deals with display, which should be in browser's TimeZone
        this.attendance.check_in =
            this.attendance.check_in && deserializeDateTime(this.attendance.check_in);
        this.attendance.check_out =
            this.attendance.check_out && deserializeDateTime(this.attendance.check_out);
        this.previous_attendance_change_date =
            action.previous_attendance_change_date &&
            deserializeDateTime(action.previous_attendance_change_date);

        const formatDateTime = registry.category("formatters").get("datetime");
        this.attendance.check_in_time =
            this.attendance.check_in && formatDateTime(this.attendance.check_in);
        this.attendance.check_out_time =
            this.attendance.check_out && formatDateTime(this.attendance.check_out);

        const formatFloatTime = registry.category("formatters").get("float_time");
        // extra hours amount displayed in the greeting message template.
        this.total_overtime_float = action.total_overtime; // Used for comparison in template
        this.total_overtime = formatFloatTime(this.total_overtime_float);
        this.today_overtime_float = action.overtime_today;
        this.today_overtime = formatFloatTime(this.today_overtime_float);

        if (action.hours_today) {
            const duration = Duration.fromObject({ hours: action.hours_today })
                .toFormat("hh-mm")
                .split("-");

            this.hours_today = sprintf(this.env._t("%(hours)s hours, %(minutes)s minutes"), {
                hours: duration[0],
                minutes: duration[1],
            });
        }

        this.employee_name = action.employee_name;
        this.attendanceBarcode = action.barcode;

        const barcode = useService("barcode");
        this.lockScanner = false;
        if (activeBarcode) {
            useBus(barcode.bus, "barcode_scanned", this.onBarcodeScanned.bind(this));
        }
    }

    async onBarcodeScanned(ev) {
        if (this.lockScanner) {
            return;
        }
        const { barcode } = ev.detail;
        if (this.attendanceBarcode !== barcode) {
            this.lockScanner = true;
            if (this.return_to_main_menu) {
                // in case of multiple scans in the greeting message view, delete the timer, a new one will be created.
                clearTimeout(this.return_to_main_menu);
            }

            const result = await this.orm.call("hr.employee", "attendance_scan", [barcode]);
            if (result.action) {
                this.actionService.doAction(result.action);
            } else if (result.warning) {
                this.notificationService.add(result.warning, { type: "danger" });
                this.setTimeoutNextAction();
                this.lockScanner = false;
            }
        }
    }

    onClickDismiss() {
        this.actionService.doAction(this.next_action, { clearBreadcrumbs: true });
    }

    async onWillStart() {
        // if no correct action given (due to an erroneous back or refresh from the browser), we set the dismiss button to return
        // to the (likely) appropriate menu, according to the user access rights
        if (!this.attendance) {
            const hasGroup = await this.user.hasGroup("hr_attendance.group_hr_attendance_user");
            if (hasGroup) {
                this.next_action = "hr_attendance.hr_attendance_action_kiosk_mode";
            } else {
                this.next_action = "hr_attendance.hr_attendance_action_my_attendances";
            }
            return;
        }

        this.setTimeoutNextAction();
        this.attendance.check_out ? this.setFarewellMessage() : this.setWelcomeMessage();
    }

    setWelcomeMessage() {
        const { _t } = this.env;
        const now = this.attendance.check_in;
        if (now.hour < 5) {
            this.state.message = _t("Good night");
        } else if (now.hour < 12) {
            if (now.hour < 8 && Math.random() < 0.3) {
                if (Math.random() < 0.75) {
                    this.state.message = _t("The early bird catches the worm");
                } else {
                    this.state.message = _t("First come, first served");
                }
            } else {
                this.state.message = _t("Good morning");
            }
        } else if (now.hour < 17) {
            this.state.message = _t("Good afternoon");
        } else if (now.hour < 23) {
            this.state.message = _t("Good evening");
        } else {
            this.state.message = _t("Good night");
        }
        if (this.previous_attendance_change_date) {
            const last_check_out_date = this.previous_attendance_change_date;
            if (now - last_check_out_date > 24 * 7 * 60 * 60 * 1000) {
                this.state.randomMessage = _t("Glad to have you back, it's been a while!");
            } else {
                if (Math.random() < 0.02) {
                    this.state.randomMessage = _t(
                        "If a job is worth doing, it is worth doing well!"
                    );
                }
            }
        }
    }

    setFarewellMessage() {
        const { _t } = this.env;
        const now = this.attendance.check_out;

        if (this.previous_attendance_change_date) {
            const last_check_in_date = this.previous_attendance_change_date;
            if (now - last_check_in_date > 1000 * 60 * 60 * 12) {
                this.state.showWarningMessage = true;
                if (this.return_to_main_menu) {
                    clearTimeout(this.return_to_main_menu);
                }
                this.lockScanner = true;
            } else if (now - last_check_in_date > 1000 * 60 * 60 * 8) {
                this.state.randomMessage = _t("Another good day's work! See you soon!");
            }
        }

        if (now.hour < 12) {
            this.state.message = _t("Have a good day!");
        } else if (now.hour < 14) {
            this.state.message = _t("Have a nice lunch!");
            if (Math.random() < 0.05) {
                this.state.randomMessage = _t(
                    "Eat breakfast as a king, lunch as a merchant and supper as a beggar"
                );
            } else if (Math.random() < 0.06) {
                this.state.randomMessage = _t("An apple a day keeps the doctor away");
            }
        } else if (now.hour < 17) {
            this.state.message = _t("Have a good afternoon");
        } else {
            if (now.hour < 18 && Math.random() < 0.2) {
                this.state.message = _t(
                    "Early to bed and early to rise, makes a man healthy, wealthy and wise"
                );
            } else {
                this.state.message = _t("Have a good evening");
            }
        }
    }

    setTimeoutNextAction() {
        if (this.kioskDelay > 0) {
            this.return_to_main_menu = setTimeout(() => {
                this.actionService.doAction(this.next_action, { clearBreadcrumbs: true });
            }, this.kioskDelay);
        }
    }

}

GreetingMessage.template = "hr_attendance.GreetingMessage";
GreetingMessage.components = { CardLayout };

registry.category("actions").add("hr_attendance_greeting_message", GreetingMessage);
