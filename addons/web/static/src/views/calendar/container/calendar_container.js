/** @odoo-module **/

import { CalendarMobileFilterPanel } from "../mobile_filter_panel/calendar_mobile_filter_panel";

const { Component, useState } = owl;

export class CalendarContainer extends Component {
    setup() {
        this.state = useState({ showSideBar: !this.env.isSmall });
    }

    get mobileFilterPanelProps() {
        return {
            model: this.props.model,
            sideBarShown: this.state.showSideBar,
            toggleSideBar: () => (this.state.showSideBar = !this.state.showSideBar),
        };
    }

    get showCalendar() {
        return !this.env.isSmall || !this.state.showSideBar;
    }

    get showSideBar() {
        return this.state.showSideBar;
    }
}
CalendarContainer.components = {
    MobileFilterPanel: CalendarMobileFilterPanel,
};
CalendarContainer.template = "web.CalendarContainer";
