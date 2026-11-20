import { Component, t, useProps } from "@odoo/owl";
import { getColor, getPaletteColor } from "../utils";

export class CalendarMobileFilterPanel extends Component {
    static components = {};
    static template = "web.CalendarMobileFilterPanel";
    props = useProps({
        model: t.object(),
        sidePanelShown: t.boolean(),
        toggleSidePanel: t.function(),
    });
    get caretDirection() {
        return this.props.sidePanelShown ? "keyboard_arrow_down" : "chevron_backward";
    }
    getFilterColorStyle(filter) {
        const color = getColor(filter.colorIndex);
        return color ? `color: ${getPaletteColor(filter.colorIndex) || color};` : "";
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
