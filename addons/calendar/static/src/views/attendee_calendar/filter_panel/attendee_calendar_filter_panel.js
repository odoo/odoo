/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";
import { CalenderAttendeeAutocomplete } from "@calendar/components/calendar_attendee_autocomplete/calendar_attendee_autocomplete";
import { Transition } from "@web/core/transition";

export class AttendeeCalendarFilterPanel extends CalendarFilterPanel {
    static components = {
        CalenderAttendeeAutocomplete,
        Transition,
    };
    static template = "calendar.AttendeeCalendarFilterPanel";

    async loadSource(section, request) {
        let records = await super.loadSource(...arguments);
        records = records.map(record => ({ ...record, model: 'res.partner' }));
        return records;
    }

    onFilterSelectCreateDialog(resModel, domain, section, dynamicFilters) {
        const title = _t("Search: %s", section.label);
        this.addDialog(SelectCreateDialog, {
            title,
            noCreate: true,
            multiSelect: true,
            resModel,
            context: {},
            domain,
            onSelected: (resId) => this.props.model.createFilter(section.fieldName, resId),
            dynamicFilters,
        });
    }
}
