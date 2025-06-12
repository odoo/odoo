import { Component } from "@odoo/owl";
import { RELATIVE_PERIODS } from "@spreadsheet/global_filters/helpers";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

const DATE_OPTIONS = [
    {
        id: "today",
        label: RELATIVE_PERIODS["today"],
    },
    {
        id: "yesterday",
        label: RELATIVE_PERIODS["yesterday"],
        separator: true,
    },
    {
        id: "last_7_days",
        label: RELATIVE_PERIODS["last_7_days"],
    },
    {
        id: "last_30_days",
        label: RELATIVE_PERIODS["last_30_days"],
    },
    {
        id: "last_90_days",
        label: RELATIVE_PERIODS["last_90_days"],
        separator: true,
    },
    {
        id: "month_to_date",
        label: RELATIVE_PERIODS["month_to_date"],
    },
    {
        id: "last_month",
        label: RELATIVE_PERIODS["last_month"],
    },
    {
        id: "this_month",
        label: _t("Current Month"),
    },
    {
        id: "this_quarter",
        label: _t("Current Quarter"),
        separator: true,
    },
    {
        id: "year_to_date",
        label: RELATIVE_PERIODS["year_to_date"],
    },
    {
        id: "last_12_months",
        label: RELATIVE_PERIODS["last_12_months"],
    },
    {
        id: "this_year",
        label: _t("Current Year"),
        separator: true,
    },
    {
        id: undefined,
        label: _t("All time"),
    },
];

/**
 * This component is used to select a default value for a date filter.
 * It displays a dropdown with predefined date options.
 */
export class DefaultDateValue extends Component {
    static template = "spreadsheet.DefaultDateValue";
    static components = { Dropdown, DropdownItem };
    static props = {
        value: { type: String, optional: true },
        update: Function,
    };

    get currentFormattedValue() {
        return (
            this.dateOptions.find((option) => option.id === this.props.value)?.label ||
            _t("All time")
        );
    }

    get dateOptions() {
        return DATE_OPTIONS;
    }
}
