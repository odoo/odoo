import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { AttendeeCalendarRenderer } from "@calendar/views/attendee_calendar/attendee_calendar_renderer";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { onWillUpdateProps } from "@odoo/owl";

const { DateTime } = luxon;

patch(AttendeeCalendarCommonRenderer.prototype, {

	setup() {
		super.setup(...arguments);
		onWillUpdateProps(() => {
			this.fc.api.setOption("businessHours", this.props.model.workingHours)
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
    onDayHeaderEvent(event, date) {
        if (event.target.closest(".o_worklocation_btn")) {
            this.handleWorkLocationClick(event.target, date);
        }
        super.onDayHeaderEvent(...arguments);
    },
    headerTemplateProps(date) {
        const parsedDate = DateTime.fromJSDate(date).toISODate();
        let workLocation = this.props.model.workLocations[parsedDate];
        const workLocationSetForCurrentUser = workLocation ?
            Object.keys(workLocation).some(key => workLocation[key].some(wlItem => wlItem.userId === user.userId)) :
            {};

        let displayedWorkLocation = workLocation ? (JSON.parse(JSON.stringify(workLocation))) : {};
        // do not display the work locations of the current user if the user filter is not active
        if (!this.props.model.data.userFilterActive) {
            for (let wl in workLocation){
                displayedWorkLocation[wl] = workLocation[wl].filter(wlItem => wlItem.userId !== user.userId);
            }
            displayedWorkLocation = Object.fromEntries(Object.entries(displayedWorkLocation).filter(([_, wlItems]) => wlItems.length !== 0));
        }

        return {
            ...super.headerTemplateProps(date),
            workLocation : displayedWorkLocation,
            workLocationSetForCurrentUser,
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
