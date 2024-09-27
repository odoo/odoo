/** @odoo-module **/

import { Component, useState, onWillUnmount } from "@odoo/owl";

const { DateTime } = luxon;
export class CardLayout extends Component {
    static template = "hr_attendance.CardLayout";
    static props = {
        kioskModeClasses: { type: String, optional: true },
        slots: Object,
        fromTrialMode: { type: Boolean, optional: true },
    };
    static defaultProps = {
        kioskModeClasses: "",
    };

    setup() {
        const now = DateTime.now();
        this.state = useState({
            dayOfWeek: now.toFormat("cccc"), // 'Wednesday'
            date: now.toLocaleString({ ...DateTime.DATE_FULL, weekday: undefined }),
            time: this.getCurrentTime(),
        });
        this.timeInterval = setInterval(() => {
            this.state.time = this.getCurrentTime();
            this.state.date = now.toLocaleString({ ...DateTime.DATE_FULL, weekday: undefined });
            this.state.dayOfWeek = now.toFormat("cccc");
        }, 1000);
        onWillUnmount(() => {
            clearInterval(this.timeInterval);
        });
    }

    getCurrentTime() {
        return DateTime.now().toLocaleString(DateTime.TIME_SIMPLE);
    }
}
