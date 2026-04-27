/** @odoo-module **/

import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import { deserializeDateTime, today } from "@web/core/l10n/dates";
import { user } from "@web/core/user";
import { Component } from "@odoo/owl";

export class DocumentsAccessExpirationDateBtn extends Component {
    static defaultProps = { editionMode: false };
    static props = {
        accessPartner: Object,
        disabled: Boolean,
        setExpirationDate: Function,
        editionMode: { type: Boolean, optional: true },
    };
    static template = "documents.AccessExpirationDateBtn";

    setup() {
        const pickerProps = {
            type: "datetime",
            value: this.props.accessPartner.expiration_date
                ? deserializeDateTime(this.props.accessPartner.expiration_date, {
                      tz: user.context.tz,
                  })
                : today(),
        };
        this.dateTimePicker = useDateTimePicker({
            target: `datetime-picker-target-${this.props.accessPartner.partner_id.id}`,
            onApply: (date) => {
                this.props.setExpirationDate(this.props.accessPartner, date);
            },
            get pickerProps() {
                return pickerProps;
            },
        });
    }

    onClickDateTimePickerBtn() {
        if (!this.props.disabled) {
            this.dateTimePicker.open();
        }
    }
}
