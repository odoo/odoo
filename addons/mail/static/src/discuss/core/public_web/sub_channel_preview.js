import { isToday } from "@mail/utils/common/dates";
import { Component } from "@odoo/owl";

const { DateTime } = luxon;

export class SubChannelPreview extends Component {
    static template = "mail.SubChannelPreview";
    static props = ["class?", "onClick?", "thread"];

    dateText(message) {
        if (isToday(message.datetime)) {
            return message.datetime?.toLocaleString(DateTime.TIME_SIMPLE);
        }
        return message.datetime?.toLocaleString(DateTime.DATE_MED);
    }

    get thread() {
        return this.props.thread;
    }

    onClick() {
        this.props.onClick?.();
    }
}
