import { Component, onWillUnmount, props, proxy, t } from "@odoo/owl";

const { DateTime } = luxon;
export class CardLayout extends Component {
    static template = "hr_attendance.CardLayout";
    props = props({
        slots: t.object(),
        fromTrialMode: t.boolean().optional(),
        companyImageUrl: t.string(),
        kioskReturn: t.function(),
        activeDisplay: t.string(),
        kioskModeClasses: t.string().optional(""),
    });

    setup() {
        this.state = proxy(this.getDateTime());
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
