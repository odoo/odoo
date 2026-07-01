import { AttendeeCalendarFilterSection } from "@calendar/views/attendee_calendar/filter/attendee_calendar_filter_section";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(AttendeeCalendarFilterSection.prototype, {
    getDeleteCalendarDialogProps(filter) {
        if (this.props.model.syncStatus?.['google_calendar'] === "sync_stopped") {
            return super.getDeleteCalendarDialogProps(filter);
        }
        return {
            ...super.getDeleteCalendarDialogProps(filter),
            body: _t("You're about to delete this calendar from Odoo.\n\n" +
                "Your calendar and all of it's events will remain in Google Calendar."),
        };
    },
});
