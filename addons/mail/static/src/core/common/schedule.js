import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";

const { DateTime } = luxon;

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class ComposerScheduleDialog extends Component {
    static template = "mail.composer_schedule_dialog";
    static components = { Dialog, DateTimePicker };
    static props = ["close"];
    static defaultProps = {};

    setup() {
        this.state = useState({
            selectedDate: null,
        });
        this.minDate = DateTime.now();
    }

    /**
     * @param {luxon.DateTime} date
     */
    onSelect(date) {
        this.selectedDate = date;
    }
}
