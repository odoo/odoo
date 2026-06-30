import { Component } from "@odoo/owl";
import { DateFilterDropdown } from "@spreadsheet/global_filters/components/date_filter_dropdown/date_filter_dropdown";
import {
    dateFilterValueToString,
    getNextDateFilterValue,
    getPreviousDateFilterValue,
} from "@spreadsheet/global_filters/helpers";
import { Dropdown } from "@web/core/dropdown/dropdown";

/**
 * This component is used to select a date filter value in a dashboard.
 * It allows the user to select a month, quarter, year, or a custom date range.
 * It also provides options for relative periods like "last 7 days", and
 * buttons to navigate through the previous and next periods.
 */
export class DashboardDateFilter extends Component {
    static template = "spreadsheet_dashboard.DashboardDateFilter";
    static components = { Dropdown, DateFilterDropdown };
    static props = {
        value: { type: Object, optional: true },
        update: Function,
    };

    get inputValue() {
        return dateFilterValueToString(this.props.value);
    }

    selectPrevious() {
        if (!this.props.value?.type) {
            return;
        }
        const previous = getPreviousDateFilterValue(this.props.value);
        if (!previous) {
            return;
        }
        this.props.update(previous);
    }

    selectNext() {
        if (!this.props.value?.type) {
            return;
        }
        const next = getNextDateFilterValue(this.props.value);
        if (!next) {
            return;
        }
        this.props.update(next);
    }
}
