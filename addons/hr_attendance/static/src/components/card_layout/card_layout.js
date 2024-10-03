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
        this.state = useState(this.getDateTime());
        this.timeInterval = setInterval(() => {
            Object.assign(this.state, this.getDateTime());
        }, 1000);
        onWillUnmount(() => {
            clearInterval(this.timeInterval);
        });
    }

    getDateTime() {
        const now = DateTime.now();
        return {
            dayOfWeek: now.toFormat("cccc"),
            date: now.toLocaleString({
                ...DateTime.DATE_FULL,
                weekday: undefined,
            }),
            time: now.toLocaleString(DateTime.TIME_SIMPLE),
        };
    }
}
