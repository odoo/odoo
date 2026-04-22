import { CalendarFilterSection } from "@web/views/calendar/calendar_filter_section/calendar_filter_section";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { CalendarFormDialog } from "@calendar/views/calendar_form/calendar_form_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class AttendeeCalendarFilterSection extends CalendarFilterSection {
    static template = "calendar.AttendeeCalendarFilterSection";
    static subTemplates = {
        filter: "calendar.AttendeeCalendarFilterSection.filter",
    };
    setup() {
        super.setup();
        this.action = useService('action')
    }
    /*
    * @override
    * Only fetch records for the current user -> extended domain before the search
    * Add a create calendar option to the selection
    * Override onSelect behavior to use existing calendar.calendar.user record
    */
    async loadSource(request) {
        const resModel = this.props.model.fields[this.section.fieldName].relation;
        const activeIds = this.section.filters.map((f) => f.value);
        const domain = [["id", "not in", activeIds], ["user_has_read_access", "=", true]];
        const records = await this.orm.call(resModel, "name_search", [], {
            name: request,
            operator: "ilike",
            domain: domain,
            limit: 8,
            context: this.section.context,
        });
        const options = records.map((result) => ({
            data: {
                id: result[0],
            },
            label: result[1],
            onSelect: async () => {
                await this.orm.call('calendar.calendar.user', 'toggle_filter', [result[0]])
                await this.props.model.load();
            },
        }));

        if (records.length > 7) {
            options.push({
                cssClass: "o_calendar_dropdown_option",
                label: _t("Search More..."),
                onSelect: () => this.onSearchMore(resModel, domain, request),
            });
        }

        if (records.length === 0) {
            options.push({
                cssClass: "o_m2o_no_result",
                label: _t("No records"),
            });
        }

        options.push({
            cssClass: "o_calendar_dropdown_option",
            label: _t("Create Calendar"),
            onSelect: () => this.createCalendar(),
        })

        return options;
    }

    createCalendar() {
        this.addDialog(FormViewDialog, {
            canExpand: false,
            resModel: "calendar.calendar",
            size: "md",
            title: _t("Calendar"),
            context: {
                form_view_ref: "calendar.calendar_calendar_view_form_dialog",
            },
            onRecordSaved: async () => {
                this.props.model.load()
            },
        });
    }

    editCalendar(filter) {
        this.addDialog(CalendarFormDialog, {
            canExpand: false,
            resModel: "calendar.calendar",
            size: "md",
            title: _t("Calendar"),
            resId: filter.value,
            removeRecord: filter.isPrimary ? undefined : () => this.deleteCalendar(filter),
            context: {
                default_calendar_id: filter.value,
                form_view_ref: "calendar.calendar_calendar_view_form_dialog",
            },
            onRecordSaved: () => {
                this.props.model.load()
            }
        });
    }

    getDeleteCalendarDialogProps(filter) {
        return {
            title: _t("Warning"),
            body: _t(
                "You're about to delete all of this calendar's events.\n" +
                "Are you sure you want to proceed?\n\n" +
                "This action cannot be reversed."
            ),
            confirmLabel: _t("Yes, delete this calendar"),
            cancelLabel: _t("Keep this calendar"),
            confirm: async () => {
                await this.orm.unlink('calendar.calendar', [filter.value]);
                await this.props.model.load()
            },
            cancel: async () => {}
        };
    }

    deleteCalendar(filter) {
        this.addDialog(ConfirmationDialog, this.getDeleteCalendarDialogProps(filter));
    }

    /*
    * @override - Always show the primary calendar first in the list
    */
    getSortedFilters() {
        return super.getSortedFilters().sort((a, b) => {
            if (a.isPrimary) return -1;
            if (b.isPrimary) return 1;
            return 0;
        });
    }
}
