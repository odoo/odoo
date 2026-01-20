import { radioField, RadioField } from "@web/views/fields/radio/radio_field";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class ScheduleTypeConfirmRadioField extends RadioField {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    /**
     * @override
     */
    async onChange(value) {
        const isCalendarReferenced = this.props.record.resId
            ? await this.orm.call("resource.calendar", "is_calendar_referenced", [
                  [this.props.record.resId],
              ])
            : null;
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

export const scheduleTypeConfirmRadioField = {
    ...radioField,
    component: ScheduleTypeConfirmRadioField,
    displayName: _t("Confirm the schedule type change"),
};

registry.category("fields").add("schedule_type_confirm_radio", scheduleTypeConfirmRadioField);
