import { AttendeeCalendarCalendarFilterSection } from "@calendar/views/attendee_calendar/filter/attendee_calendar_filter_section";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";

patch(AttendeeCalendarCalendarFilterSection.prototype, {
    getDeleteCalendarDialogProps(filter) {
        if (this.props.model.syncStatus?.['google_calendar'] === "sync_stopped") {
            return super.getDeleteCalendarDialogProps(filter);
        }
        return {
            ...super.getDeleteCalendarDialogProps(filter),
            body: _t("You're about to delete this calendar from Odoo.\n\n" +
                "If you synchronized this calendar with Google, it will not be deleted from your Google Calendar."),
        };
    },

    getFilterDomain(activeIds) {
        const domain = super.getFilterDomain(activeIds);
        return Domain.and([domain, [['is_import_pending', '=', false]]]).toList();
    }
});
