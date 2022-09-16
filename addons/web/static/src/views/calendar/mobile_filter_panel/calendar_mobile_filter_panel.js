/** @odoo-module **/

import { CalendarFilterPanel } from "../filter_panel/calendar_filter_panel";

const { Component } = owl;

export class CalendarMobileFilterPanel extends Component {
    get caretDirection() {
        return this.props.sideBarShown ? "down" : "left";
    }
    getFilterTypePriority(type) {
        return ["user", "record", "dynamic", "all"].indexOf(type);
    }
    getSortedFilters(section) {
        return section.filters.slice().sort((a, b) => {
            if (a.type === b.type) {
                const va = a.value ? -1 : 0;
                const vb = b.value ? -1 : 0;
                if (a.type === "dynamic" && va !== vb) {
                    return va - vb;
                }
                return b.label.localeCompare(a.label);
            } else {
                return this.getFilterTypePriority(a.type) - this.getFilterTypePriority(b.type);
            }
        });
    }
}
CalendarMobileFilterPanel.components = {
    FilterPanel: CalendarFilterPanel,
};
CalendarMobileFilterPanel.template = "web.CalendarMobileFilterPanel";
