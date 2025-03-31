import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { AttendeeCalendarRenderer } from "@calendar/views/attendee_calendar/attendee_calendar_renderer";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { onWillUpdateProps, onPatched } from "@odoo/owl";
import { renderToString } from "@web/core/utils/render";

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
			eventOrder: function(event1, event2) {
                if (event1.extendedProps.workLocation){
                    return -1;
                } else {
                    if(event2.extendedProps.workLocation){
                        return 1;
                    } else {
                        return event1.title.localeCompare(event2.title);
                    }
                }
            },
            dayCellDidMount: this.onDayCellDidMount,
            dayHeaderDidMount: this.onDayHeaderDidMount,
            dayHeaderWillUnmount: this.onDayHeaderWillUnmount,
		};
	},
	handleWorkLocationClick(target, date) {
        let workLocations = this.props.model.workLocations[date.toISODate()];
        const workLocationSet = workLocations && Object.keys(workLocations).length > 0;
        const actionElement = target.closest('.wl_action');
        if (!actionElement) {
            return;
        }
        const { location, id, create } = actionElement.dataset;
        if (workLocationSet && !create) {
            if (!workLocations.id) {
                workLocations = workLocations[location] && workLocations[location].find(wl => wl.id == id);
            }
            if (workLocations) {
                return this.openPopover(target, workLocations);
            }
        }
        return this.props.openWorkLocationWizard(date);
    },
    onDayHeaderDidMount(info) {
        if (this.props.model.scale === 'week' || this.props.model.scale === 'day') {
            const date = DateTime.fromJSDate(info.date);
            const handler = (event) => {
                if (event.target.closest(".o_worklocation_btn")) {
                    this.handleWorkLocationClick(event.target, date);
                }
            };
            this.customListeners = {
                ...this.customListeners,
                [date]: handler,
            };
            info.el.addEventListener("click", handler);
        }
    },
    onDayHeaderWillUnmount(info) {
        if (this.props.model.scale === 'week' || this.props.model.scale === 'day') {
            const date = DateTime.fromJSDate(info.date);
            const customListener = {...this.customListeners}[date];
            if (customListener) {
                info.el.removeEventListener("click", customListener);
                delete this.customListeners[date];
            }
        }
    },
    onDayCellDidMount(info){
        if (this.props.model.scale === 'month'){
            const box = info.el.querySelector(`.fc-daygrid-day-top`);
            if (!box)
                return;
            const content = renderToString(this.constructor.ButtonWorklocationTemplate, this.headerTemplateProps(info.date));
            box.insertAdjacentHTML("beforeend", content);
        }
    },
    headerTemplateProps(date) {
        if (this.props.model.scale === "month") {
            return super.headerTemplateProps(date);
        }
        const parsedDate = DateTime.fromJSDate(date).toISODate();
        const multiCalendar = this.props.model.multiCalendar;
        const showLine = ["week", "month"].includes(this.props.model.scale);
        let workLocation = this.props.model.workLocations[parsedDate];
        const workLocationSetForCurrentUser =
            multiCalendar ?
            Object.keys(workLocation).some(key => workLocation[key].some(wlItem => wlItem.userId === user.userId)
            ) : workLocation?.userId === user.userId;

        let displayedWorkLocation = workLocation ? (JSON.parse(JSON.stringify(workLocation))) : {};
        // do not display the work locations of the current user if the user filter is not active
        if (multiCalendar && !this.props.model.data.userFilterActive) {
            for (let wl in workLocation){
                displayedWorkLocation[wl] = workLocation[wl].filter(wlItem => wlItem.userId !== user.userId);
            }
            displayedWorkLocation = Object.fromEntries(Object.entries(displayedWorkLocation).filter(([_, wlItems]) => wlItems.length !== 0));
        }

        return {
            ...super.headerTemplateProps(date),
            workLocation : displayedWorkLocation,
            workLocationSetForCurrentUser,
            multiCalendar,
            showLine,
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

AttendeeCalendarCommonRenderer.WorklocationTemplate = "hr_homeworking_calendar.CalendarCommonRenderer.worklocation";
AttendeeCalendarCommonRenderer.ButtonWorklocationTemplate = "hr_homeworking_calendar.CalendarCommonRenderer.buttonWorklocation";
AttendeeCalendarCommonRenderer.headerTemplate = "hr_homeworking_calendar.CalendarCommonRendererHeader";
