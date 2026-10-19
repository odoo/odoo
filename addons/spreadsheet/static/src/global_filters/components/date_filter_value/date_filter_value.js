import { Component, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DateFilterDropdown } from "../date_filter_dropdown/date_filter_dropdown";
import { dateFilterValueToString } from "@spreadsheet/global_filters/helpers";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

/**
 * This component is used to select a date filter value.
 * It allows the user to select a month, quarter, year, or a custom date range.
 * It also provides options for relative periods like "last 7 days".
 */
export class DateFilterValue extends Component {
    static template = "spreadsheet.DateFilterValue";
    static components = { Dropdown, DateFilterDropdown };
    props = useProps({
        value: t.object().optional(),
        update: t.function(),
        model: t.object(),
    });

    setup() {
        this.dropdownState = useDropdownState();
    }

    onInputClick() {
        this.dropdownState.open();
    }

    get inputValue() {
        return dateFilterValueToString(this.props.value, this.props.model.getters);
    }
}
