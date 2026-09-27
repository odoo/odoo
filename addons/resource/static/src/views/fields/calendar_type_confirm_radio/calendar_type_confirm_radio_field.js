import { radioField, RadioField } from "@web/views/fields/radio/radio_field";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class CalendarTypeConfirmRadioField extends RadioField {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    /**
     * @override
     */
    async onChange(value) {
        if (!this.props.record.resId) {
            super.onChange(...arguments);
            this.props.record.save();
        } else {
            const isCalendarReferenced = await this.orm.call(
                "resource.calendar",
                "is_calendar_referenced",
                [[this.props.record.resId]]
            );
            if (isCalendarReferenced) {
                this.dialog.add(ConfirmationDialog, {
                    title: "Calendar Type Change",
                    body: _t(
                        "Are you sure? This calendar is already used.\nAll the attendances will be deleted for this calendar"
                    ),
                    confirmLabel: _t("Continue"),
                    confirm: () => {
                        super.onChange(...arguments);
                        this.props.record.save();
                    },
                    cancel: () => this.props.record.load(),
                });
            } else {
                super.onChange(...arguments);
            }
        }
    }
}

export const calendarTypeConfirmRadioField = {
    ...radioField,
    additionalClasses: ["o_field_radio"],
    component: CalendarTypeConfirmRadioField,
    displayName: _t("Confirm the calendar type change"),
};

registry.category("fields").add("form.calendar_type_confirm_radio", calendarTypeConfirmRadioField);
