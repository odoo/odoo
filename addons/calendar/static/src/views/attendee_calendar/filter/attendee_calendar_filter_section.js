import { CalendarFilterSection } from "@web/views/calendar/calendar_filter_section/calendar_filter_section";
import { _t } from "@web/core/l10n/translation";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { CalendarFormDialog } from "@calendar/views/calendar_form/calendar_form_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { Domain } from '@web/core/domain';
import { user } from "@web/core/user";

export class AttendeeCalendarCalendarFilterSection extends CalendarFilterSection {
    static template = "calendar.AttendeeCalendarCalendarFilterSection";
    static subTemplates = {
        filter: "calendar.AttendeeCalendarCalendarFilterSection.filter",
    };

    setup() {
        super.setup();
        this.action = useService('action')
    }

    /*
    * @override
    * Only fetch records for the current user -> extended domain before the search
    * Add a 'Create Calendar' and 'All calendars' options to the selection
    * Override onSelect behavior to use existing calendar.user record
    */
    async loadSource(request) {
        const options = await super.loadSource(request);

        options.push({
            cssClass: "o_calendar_dropdown_option",
            label: _t("Create Calendar"),
            onSelect: () => this.createCalendar(),
        })

        options.push({
            cssClass: "o_calendar_dropdown_option",
            label: _t("All calendars"),
            onSelect: () => this.action.doAction("calendar.action_calendar_calendar")
        })

        return options;
    }

    getFilterDomain(activeIds) {
        const domain = super.getFilterDomain(activeIds);
        return Domain.and([domain, [["calendar_user_ids", "any", [["user_id", "=", user.userId]]]]]).toList();
    }

    async onFilterSelected(filterRecord) {
        await this.orm.call('calendar.calendar', 'add_filter_to_list', [filterRecord[0]])
        await this.props.model.load();
    }

    createCalendar() {
        this.addDialog(FormViewDialog, {
            canExpand: false,
            resModel: "calendar.calendar",
            size: "md",
            title: _t("New Calendar"),
            onRecordSaved: async () => {
                this.props.model.load()
            },
        });
    }
    /*
    * Owners of a calendar can edit the calendar record directly. Non-owners can only edit the
    * calendar_user record which edits their user-specific settings for it. Similarly, only the
    * owner of a calendar can delete it, non-owners can instead 'unsubscribe'
    */
    editCalendar(filter) {
        this.addDialog(CalendarFormDialog, {
            canExpand: false,
            resModel: filter.accessRole === 'owner' ? "calendar.calendar" : "calendar.user",
            size: "md",
            title: _t("Edit Calendar"),
            resId: filter.accessRole === 'owner' ? filter.value : filter.recordId,
            removeRecord: filter.isPrimary ? undefined : () => this.deleteCalendar(filter),
            context: {
                default_calendar_id: filter.value,
            },
            onRecordSaved: async () => {
                this.props.model.load()
            }
        });
    }

    getDeleteCalendarDialogProps(filter) {
        return {
            title: _t("Warning"),
            body: _t(
                "If you are the only person using this calendar, all of it's events will be deleted." +
                "Are you sure you want to proceed?\n\n" +
                "This action cannot be reversed."
            ),
            confirmLabel: _t("Yes, delete this calendar"),
            cancelLabel: _t("Keep this calendar"),
            confirm: async () => {
                await this.orm.unlink('calendar.user', [filter.recordId]);
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
