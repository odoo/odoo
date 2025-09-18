// @ts-check

/** @module @web/views/calendar/mobile_filter_panel/calendar_mobile_filter_panel - Compact filter panel for mobile calendar with sidebar toggle */

import { Component } from "@odoo/owl";
import { getColor } from "@web/views/calendar/calendar_utils";

/** Compact filter panel for mobile calendar view with toggle sidebar support. */
export class CalendarMobileFilterPanel extends Component {
    static components = {};
    static template = "web.CalendarMobileFilterPanel";
    static props = {
        model: Object,
        sideBarShown: Boolean,
        toggleSideBar: Function,
    };
    /** @returns {"down" | "left"} caret icon direction based on sidebar visibility */
    get caretDirection() {
        return this.props.sideBarShown ? "down" : "left";
    }
    /**
     * @param {{ colorIndex: number }} filter - calendar filter descriptor
     * @returns {string} CSS color class for the filter badge
     */
    getFilterColor(filter) {
        return `o_color_${getColor(filter.colorIndex)}`;
    }
    /**
     * @param {string} type - filter type ("user", "record", "dynamic", "all")
     * @returns {number} sort priority index for the filter type
     */
    getFilterTypePriority(type) {
        return ["user", "record", "dynamic", "all"].indexOf(type);
    }
    /**
     * @param {{ filters: Array<{ type: string, value: any, label: string }> }} section - filter section
     * @returns {Array} filters sorted by type priority, then alphabetically by label
     */
    getSortedFilters(section) {
        return section.filters.toSorted((a, b) => {
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
                return (
                    this.getFilterTypePriority(a.type) -
                    this.getFilterTypePriority(b.type)
                );
            }
        });
    }
}
