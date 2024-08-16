/** @ts-check */

import { Component } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { serializeDate, deserializeDate } from "@web/core/l10n/dates";

export class DateFromToValue extends Component {
    static template = "spreadsheet.DateFromToValue";
    static components = { DateTimeInput };
    static props = {
        onFromToChanged: Function,
        from: { type: String, optional: true },
        to: { type: String, optional: true },
    };

    onDateFromChanged(dateFrom) {
        this.props.onFromToChanged({
            from: dateFrom ? serializeDate(dateFrom.startOf("day")) : undefined,
            to: this.props.to,
        });
    }

    onDateToChanged(dateTo) {
        this.props.onFromToChanged({
            from: this.props.from,
            to: dateTo ? serializeDate(dateTo.endOf("day")) : undefined,
        });
    }

    get dateFrom() {
        return this.props.from && deserializeDate(this.props.from);
    }

    get dateTo() {
        return this.props.to && deserializeDate(this.props.to);
    }
}
