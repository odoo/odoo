import { CalendarController } from "@web/views/calendar/calendar_controller";
import { _t } from "@web/core/l10n/translation";

export class EventSlotCalendarController extends CalendarController {

    /**
     * @override
     * Hide sidebar on mobile if there are no filters.
     */
    get hasSideBar() {
        return (!this.env.isSmall && this.model.showDatePicker) || this.model.filterSections.length > 0;
    }

    /**
     * Rename quick create dialog.
     * Load model after save to show created record.
     */
    getQuickCreateFormViewProps(record) {
        return {
            ...super.getQuickCreateFormViewProps(record),
            onRecordSaved: () => this.model.load(),
            title: _t("New Slot"),
        };
    }
}
