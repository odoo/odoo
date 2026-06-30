import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { AttendeeCalendarRenderer } from "@calendar/views/attendee_calendar/attendee_calendar_renderer";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { onWillUpdateProps, onPatched } from "@odoo/owl";

const { DateTime } = luxon;

patch(AttendeeCalendarCommonRenderer.prototype, {
	setup() {
		super.setup(...arguments);
		onWillUpdateProps(() => {
			this.fc.api.setOption("businessHours", this.props.model.workingHours)
		});
		onPatched(() => {
            // Force to rerender the FC.
            // As it doesn't redraw the header when the event's data changes
            this.fc.api.render();
        });
	},
	get options() {
		return {
            ...super.options,
			businessHours: this.props.model.workingHours,
        };
	},
	handleWorkLocationClick(target, date) {
        let worklocations = this.props.model.worklocations[date.toISODate()];
        const worklocationSet = worklocations && Object.keys(worklocations).length > 0;
        const actionElement = target.closest('.o_worklocation_action');
        if (!actionElement) {
            return;
        }
        const { location, id, create } = actionElement.dataset;
        if (worklocationSet && !create) {
            if (!worklocations.id) {
                worklocations = worklocations[location] && worklocations[location].find(wl => wl.id == id);
            }
            // If the worklocation doesn't belong to the current user, open a popover instead of the wizard
            if (worklocations && worklocations.userId !== user.userId) {
                return this.openPopover(target, worklocations);
            }
            return this.props.openWorkLocationWizard(date, worklocations.work_location_id, worklocations.ghostRecord);
        }
        return this.props.openWorkLocationWizard(date);
    },
    onDateClick(info){
        if (info.jsEvent && info.jsEvent.target.closest(".o_worklocation_btn")) {
            const date = DateTime.fromJSDate(info.date);
            this.handleWorkLocationClick(info.jsEvent.target, date);
        } else {
            super.onDateClick(...arguments)
        }
    },
    headerTemplateProps(date) {
        const parsedDate = DateTime.fromJSDate(date).toISODate();
        let showLine = this.props.model.scale === "week";
        let worklocation = this.props.model.worklocations[parsedDate];
        if (!worklocation) {
            return {
                ...super.headerTemplateProps(date),
                showLine,
                userFilterActive: this.props.model.data.userFilterActive,
                hideWorkLocation: false,
            };
        }
        const multiCalendar = this.props.model.multiCalendar;
        const workLocationSetForCurrentUser =
            multiCalendar && worklocation ?
            Object.keys(worklocation).some(key => worklocation[key].some(wlItem => wlItem.userId === user.userId)
            ) : worklocation?.userId === user.userId;

        let displayedWorkLocation = worklocation ? (JSON.parse(JSON.stringify(worklocation))) : {};
        // do not display the work locations of the current user if the user filter is not active
        if (!this.props.model.data.userFilterActive) {
            if (multiCalendar) {
                for (let wl in worklocation){
                    displayedWorkLocation[wl] = worklocation[wl].filter(wlItem => wlItem.userId !== user.userId);
                }
                displayedWorkLocation = Object.fromEntries(Object.entries(displayedWorkLocation).filter(([_, wlItems]) => wlItems.length !== 0));
            } else {
                displayedWorkLocation = {};
                showLine = false;
            }
        }

        return {
            ...super.headerTemplateProps(date),
            worklocation : displayedWorkLocation,
            workLocationSetForCurrentUser,
            multiCalendar,
            hideWorkLocation: false,
            showLine,
            userFilterActive: this.props.model.data.userFilterActive,
            iconMap: {
                "office": "fa-building",
                "home": "fa-home",
            },
        }
    }
});

AttendeeCalendarRenderer.props = {
    ...AttendeeCalendarRenderer.props,
    openWorkLocationWizard: { type: Function, optional: true },
}
AttendeeCalendarCommonRenderer.props = {
    ...AttendeeCalendarCommonRenderer.props,
    openWorkLocationWizard: { type: Function, optional: true }
};

AttendeeCalendarCommonRenderer.WorklocationTemplate = "hr_calendar.CalendarCommonRenderer.worklocation";
AttendeeCalendarCommonRenderer.ButtonWorklocationTemplate = "hr_calendar.CalendarCommonRenderer.buttonWorklocation";
AttendeeCalendarCommonRenderer.headerTemplate = "hr_calendar.CalendarCommonRendererHeader";
