/** @odoo-module **/

import { Component, useState, onWillUnmount } from "@odoo/owl";
import { url } from "@web/core/utils/urls";
import { browser } from "@web/core/browser/browser";

const { DateTime } = luxon;
export class CardLayout extends Component {
    static template = "hr_attendance.CardLayout";
    static props = {
        kioskModeClasses: { type: String, optional: true },
        slots: Object,
    };
    static defaultProps = {
        kioskModeClasses: "",
    };

    setup() {
        const now = DateTime.now();
        this.state = useState({
            dayOfWeek: now.toFormat('cccc'), // 'Wednesday'
            date: now.toLocaleString({ ...DateTime.DATE_FULL, weekday: undefined }),
            time: now.toLocaleString(DateTime.TIME_SIMPLE)
        });
        this.timeInterval = setInterval(() => {
            const now = DateTime.now();
            this.state.dayOfWeek = now.toFormat('cccc');
            this.state.date = now.toLocaleString({ ...DateTime.DATE_FULL, weekday: undefined });
            this.state.time = now.toLocaleString(DateTime.TIME_SIMPLE);
        }, 1000);
        this.companyImageUrl = url("/web/binary/company_logo", {
            company: this.props.companyId,
        });
        onWillUnmount(() => {
            clearInterval(this.timeInterval);
        });
    }

    get showDemoMessage() {
        return true;
    }

    removeDemoMessage(){
        browser.localStorage.setItem("hr_attendance.noShowDemoMessage", true);
        return;
    }

    getCurrentTime() {
        return DateTime.now().toLocaleString(DateTime.TIME_SIMPLE);
    }

}
