/** @odoo-module */

import { DateTimeInput } from '@web/core/datetime/datetime_input';
import { Dialog } from "@web/core/dialog/dialog";

import { Component } from "@odoo/owl";
const { DateTime } = luxon;

export class ExpectedDateDialog extends Component {
    static template = "account_reports.ExpectedDateDialog";
    static components = {
        DateTimeInput,
        Dialog,
    };
    static props = {
        close: {type: Function},
        save: {type: Function},
        title: {type: String},
        size: {type: String},
        default_date: {type: DateTime, optional: true},
    };

    _save(ev) {
        this.props.save(ev, this.date);
        this.props.close();
    }

    _cancel() {
        this.props.close();
    }

    onDateTimeChanged(date) {
        this.date = date;
    }
}
