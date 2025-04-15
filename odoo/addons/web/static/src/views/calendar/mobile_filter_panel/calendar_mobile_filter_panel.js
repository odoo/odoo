/** @odoo-module **/

import { Component } from "@odoo/owl";
import { getColor } from "../colors";

export class CalendarMobileFilterPanel extends Component {
    get caretDirection() {
        return this.props.sideBarShown ? "down" : "left";
    }
    getFilterColor(filter) {
        return `o_color_${getColor(filter.colorIndex)}`;
    }
    getFilterTypePriority(type) {
        return ["user", "record", "dynamic", "all"].indexOf(type);
    }
    getSortedFilters(section) {
        return section.filters.slice().sort((a, b) => {
            if (a.type === b.type) {
                const va = a.value ? -1 : 0;
                const vb = b.value ? -1 : 0;
                //Condition to put unvaluable item (eg: Open Shifts) at the end of the sorted list.
                if (a.type === "dynamic" && va !== vb) {
                    return va - vb;
                }
                return a.label.localeCompare(b.label, undefined, {
                    numeric: true,
                    sensitivity: "base",
                    ignorePunctuation: true,
                });
            } else {
                return this.getFilterTypePriority(a.type) - this.getFilterTypePriority(b.type);
            }
        });
    }
}
CalendarMobileFilterPanel.components = {};
CalendarMobileFilterPanel.template = "web.CalendarMobileFilterPanel";
