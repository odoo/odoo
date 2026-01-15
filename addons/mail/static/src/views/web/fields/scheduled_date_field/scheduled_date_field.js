import { ScheduledDateDialog } from "./scheduled_date_dialog";
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

/**
 * Widgets used to display and select the scheduled date in the composer (in monocomment mode)
 * and in the mail_scheduled_message form view.
 * There are two different widgets because the composer uses a text field to store the
 * scheduled date whereas the mail_scheduled_message model uses a datetime field.
 */

class ScheduledDateFieldCommon extends Component {
    static props = standardFieldProps;
    static template = "mail.ScheduledDateField";

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.dateTimeFormat = {
            day: "numeric",
            hour: "numeric",
            minute: "numeric",
            month: "short",
        };
    }

    onClick(ev) {
        this.dialog.add(ScheduledDateDialog, {
            save: (scheduledDate) => this.setScheduledDate(scheduledDate),
            isRemovable: this.isRemovable,
            scheduledDate: this.scheduledDate,
        });
        // prevents the button to look focused (text-info to look darker) when closing the dialog
        ev.currentTarget.blur();
    }
}

class TextScheduledDateField extends ScheduledDateFieldCommon {
    setup() {
        super.setup();
        this.isRemovable = true;
    }

    get scheduledDate() {
        return (
            (this.props.record.data[this.props.name] || undefined) &&
            deserializeDateTime(this.props.record.data[this.props.name])
        );
    }

    setScheduledDate(scheduledDate) {
        this.props.record.update({
            scheduled_date: scheduledDate ? serializeDateTime(scheduledDate) : "",
        });
    }
}

const textScheduledDateField = {
    component: TextScheduledDateField,
};
registry.category("fields").add("text_scheduled_date", textScheduledDateField);

class DatetimeScheduledDateField extends ScheduledDateFieldCommon {
    setup() {
        super.setup();
        this.isRemovable = false;
    }

    get scheduledDate() {
        return this.props.record.data[this.props.name];
    }

    setScheduledDate(scheduledDate) {
        this.props.record.update({ scheduled_date: scheduledDate });
    }
}

const datetimeScheduledDateField = {
    component: DatetimeScheduledDateField,
};
registry.category("fields").add("datetime_scheduled_date", datetimeScheduledDateField);
