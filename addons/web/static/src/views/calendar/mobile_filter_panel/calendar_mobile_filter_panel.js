/** @odoo-module **/

import { Component } from "@odoo/owl";

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
CalendarMobileFilterPanel.components = {};
CalendarMobileFilterPanel.template = "web.CalendarMobileFilterPanel";
