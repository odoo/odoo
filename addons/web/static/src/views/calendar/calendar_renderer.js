/** @odoo-module **/

import { CalendarCommonRenderer } from "./calendar_common/calendar_common_renderer";
import { CalendarYearRenderer } from "./calendar_year/calendar_year_renderer";

const { Component } = owl;

export class CalendarRenderer extends Component {
    get calendarComponent() {
        return this.constructor.components[this.props.model.scale];
    }
    get calendarKey() {
        return `${this.props.model.scale}_${this.props.model.date.valueOf()}`;
    }
}
CalendarRenderer.components = {
    day: CalendarCommonRenderer,
    week: CalendarCommonRenderer,
    month: CalendarCommonRenderer,
    year: CalendarYearRenderer,
};
CalendarRenderer.template = "web.CalendarRenderer";
