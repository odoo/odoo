
import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarCommonRenderer.prototype, {
    get options(){
        return {
            ...super.options,
            dayHeaderClassNames: this.onDayHeaderClassNames,
        }
    },

    // getDayCellClassNames(info){
    //     const date = luxon.DateTime.fromJSDate(info.date).toISODate();
    //     const record = this.props.model.data.mandatoryDaysList[date];
    //     if (record) {
    //         return [`o_mandatory_day_${record.color}`];
    //     }
    // },

    // onDayHeaderClassNames(info){
    //     const date = luxon.DateTime.fromJSDate(info.date).toISODate();
    //     const record = this.props.model.data.mandatoryDaysList[date];
    //     if (record) {
    //         return [`o_mandatory_day_${record.color}`];
    //     }
    // },

    headerTemplateProps(date) {
        const parsedDate = luxon.DateTime.fromJSDate(date).toISODate();
        let title = "";
        let color = "";
        if (this.props.model.data.mandatoryDaysList[parsedDate]) {
            title = this.props.model.data.mandatoryDaysList[parsedDate].title;
            color = this.props.model.data.mandatoryDaysList[parsedDate].color;
        }
        return {
            ...super.headerTemplateProps(date),
            title : title,
            color: color,
        }
    }
})
