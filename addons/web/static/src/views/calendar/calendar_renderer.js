/** @odoo-module **/

import { ActionSwiper } from "@web/core/action_swiper/action_swiper";
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
    get actionSwiperProps() {
        return {
            onLeftSwipe: this.env.isSmall
                ? { action: () => this.props.setDate("next") }
                : undefined,
            onRightSwipe: this.env.isSmall
                ? { action: () => this.props.setDate("previous") }
                : undefined,
            animationOnMove: false,
            animationType: "forwards",
            swipeDistanceRatio: 6,
        };
    }
}
CalendarRenderer.components = {
    day: CalendarCommonRenderer,
    week: CalendarCommonRenderer,
    month: CalendarCommonRenderer,
    year: CalendarYearRenderer,
    ActionSwiper,
};
CalendarRenderer.template = "web.CalendarRenderer";
