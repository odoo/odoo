import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { patch } from "@web/core/utils/patch";
import { usePopover } from "@web/core/popover/popover_hook";
import { Component } from "@odoo/owl";

class HolidayPopover extends Component {
    static template = "hr_holidays.holidayPopover";
    static props = {
        title: String,
        color: Number,
        jobs: { optional: true, type: Array },
        departments: { optional: true, type: Array },
        icon: String,
        close: { optional: true, type: Function }
    };
}

patch(AttendeeCalendarCommonRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.holidaysPopover = usePopover(HolidayPopover, { position: 'right' });
    },
    get options() {
        return {
            ...super.options,
            dayHeaderClassNames: this.onDayHeaderClassNames,
        }
    },

    headerTemplateProps(date) {
        const parsedDate = luxon.DateTime.fromJSDate(date).toISODate();
        return {
            ...super.headerTemplateProps(date),
            mandatory_day_list : this.props.model.data.mandatoryDaysList[parsedDate] || [],
            public_holiday_list: this.props.model.data.publicHolidayList[parsedDate] || [],
        }
    },

    onDayHeaderEvent(event, date) {
        if (event.target.closest(".holiday_icon")) {
            this.openSpecialDayInfo(event.target, date);
        }
        super.onDayHeaderEvent(...arguments);
    },

    async openSpecialDayInfo(target, date) {
        const data = this.props.model.data;
        const dataset = target.closest(".holiday_icon").dataset;
        const modelName = dataset.model;
        const daysArray = modelName == "mandatory_day" ? data.mandatoryDaysList : data.publicHolidayList;
        const modelIndex = dataset.index;
        let specialDay = daysArray[date.toISODate()][modelIndex];
        return this.holidaysPopover.open(target, {
            title: specialDay.title,
            jobs: specialDay.jobs_name,
            departments: specialDay.departments_name,
            color: specialDay.color,
            icon: specialDay.icon,
        });
    }
})