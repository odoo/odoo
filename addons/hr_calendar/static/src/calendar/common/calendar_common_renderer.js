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
            /*The fc.api.render() only re-renders content handled by its internal virtual DOM
            and content added using methods like dayCellContent or eventContent
            (https://fullcalendar.io/docs/content-injection)

            Since the dayCell content is injected into the DOM using standard js,
            the lib doesn't know about it and won't rerender it

            From the docs (https://fullcalendar.io/docs/Calendar-render):
            'This method will not completely wipe the DOM clean and rebuild. It will use its
            internal virtual DOM representation to only commit needed changes.'*/
            this.renderMonthDayCellsWorklocations();
        });
	},
	get options() {
		return {
            ...super.options,
			businessHours: this.props.model.workingHours,
            eventOrder: function(event1, event2){
                if (event1.extendedProps.worklocation){
                    return -1;
                } else {
                    if(event2.extendedProps.worklocation){
                        return 1;
                    } else {
                        return event1.start < event2.start ? -1 : 1;
                    }
                }
            },
            dayCellDidMount: this.onDayCellDidMount,
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
    onDayCellDidMount(info){
        if (this.props.model.scale === 'month'){
            const box = info.el.querySelector(`.fc-daygrid-day-top`);
            if (!box)
                return;
            const content = renderToString(this.constructor.ButtonWorklocationTemplate, this.headerTemplateProps(info.date));
            box.insertAdjacentHTML("beforeend", content);
        }
    },
    // Manually rerender injected worklocation html content (see onPatched in setup)
    renderMonthDayCellsWorklocations() {
        if (this.props.model.scale === 'month') {
            const dayCells = document.querySelectorAll('.fc-daygrid-day');
            dayCells.forEach(dayCell => {
                const wlButtonEl = dayCell.querySelector('.o_worklocation_btn');
                if (wlButtonEl) {
                    wlButtonEl.remove();

                    const dayTopEl = dayCell.querySelector('.fc-daygrid-day-top');
                    if (!dayTopEl) {
                        return;
                    }

                    const dateStr = dayCell.getAttribute('data-date');
                    if (!dateStr) {
                        return;
                    }

                    const date = new Date(dateStr);
                    const wlContent = renderToString(this.constructor.ButtonWorklocationTemplate, this.headerTemplateProps(date));
                    dayTopEl.insertAdjacentHTML("beforeend", wlContent);
                }
            });
        }
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
        let showLine = ["week", "month"].includes(this.props.model.scale);
        let worklocation = this.props.model.worklocations[parsedDate];
        if (!worklocation) {
            return {...super.headerTemplateProps(date), showLine, userFilterActive: this.props.model.data.userFilterActive};
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
