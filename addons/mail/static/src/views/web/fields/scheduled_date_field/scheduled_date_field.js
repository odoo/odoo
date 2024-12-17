import { ScheduledDateDialog } from "./scheduled_date_dialog";
import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

/**
 * Widget used to display and select the scheduled date in the composer (in monocomment mode)
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

class MailComposerScheduledDateField extends ScheduledDateFieldCommon {
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

const mailComposerScheduledDateField = {
    component: MailComposerScheduledDateField,
};
registry.category("fields").add("mail_composer_scheduled_date", mailComposerScheduledDateField);

class MailScheduledMessageScheduledDateField extends ScheduledDateFieldCommon {
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

const mailScheduledMessageScheduledDateField = {
    component: MailScheduledMessageScheduledDateField,
};
registry
    .category("fields")
    .add("mail_scheduled_message_scheduled_date", mailScheduledMessageScheduledDateField);
