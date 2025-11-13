import { Component, onWillUpdateProps } from "@odoo/owl";
import {
    dateFilterValueToString,
    getDateRange,
    getNextDateFilterValue,
    getPreviousDateFilterValue,
    globalFilterDateRegistry,
    getDateGlobalFilterTypes,
} from "@spreadsheet/global_filters/helpers";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
const { DateTime } = luxon;

/**
 * This component is used to select a date filter value.
 * It allows the user to select a month, quarter, year, or a custom date range.
 * It also provides options for relative periods like "last 7 days".
 */
export class DateFilterDropdown extends Component {
    static template = "spreadsheet.DateFilterDropdown";
    static components = { DropdownItem, DateTimeInput };
    static props = {
        value: { type: Object, optional: true },
        update: Function,
        model: Object,
    };

    setup() {
        this._computeDefaultSelectedValues();
        this._applyCurrentValueToSelectedValues(this.props.value);
        onWillUpdateProps((nextProps) => this._applyCurrentValueToSelectedValues(nextProps.value));
    }

    /**
     * Computes the default selected values based on the current date.
     */
    _computeDefaultSelectedValues() {
        const now = DateTime.local();
        const fixedPeriodsTypes = getDateGlobalFilterTypes().filter(
            (type) => globalFilterDateRegistry.get(type).isFixedPeriod
        );

        this.selectedValues = {};
        for (const type of fixedPeriodsTypes) {
            this.selectedValues[type] = globalFilterDateRegistry
                .get(type)
                .getCurrentFixedPeriod(now);
        }
    }

    /**
     * Updates the default selected values based on the current value.
     * This method is called whenever the component's props are updated.
     */
    _applyCurrentValueToSelectedValues(value) {
        this._setRangeToCurrentValue(value);
        if (value?.type) {
            const filterType = value.type === "relative" ? value.period : value.type;
            if (this.isFixedPeriod(filterType)) {
                this.selectedValues[value.type] = { ...value };
            }
        }
    }

    _setRangeToCurrentValue(value) {
        const now = DateTime.local();
        const { from, to } = getDateRange(value, 0, now, this.props.model.getters);
        this.selectedValues.range = {
            type: "range",
            from: from ? from.toISODate() : now.startOf("month").toISODate(),
            to: to ? to.toISODate() : now.endOf("month").toISODate(),
        };
    }

    get dateOptions() {
        const filterTypes = getDateGlobalFilterTypes().filter((type) => {
            const item = globalFilterDateRegistry.get(type);
            return !item.canOnlyBeDefault && !item.shouldBeHidden?.(this.props.model.getters);
        });
        const options = filterTypes.map((type, i) => {
            const item = globalFilterDateRegistry.get(type);
            const nextItem = filterTypes[i + 1] && globalFilterDateRegistry.get(filterTypes[i + 1]);
            return {
                type,
                label: item.label,
                separator: nextItem && nextItem.category !== item.category,
            };
        });

        const rangeIndex = options.findIndex((option) => option.type === "range");
        if (rangeIndex !== -1) {
            options.splice(rangeIndex, 0, { type: undefined, label: _t("All time") });
        }
        return options;
    }

    isSelected(value) {
        if (!this.props.value) {
            return value.type === undefined;
        }
        if (this.props.value.type === "relative") {
            return this.props.value.period === value.type;
        }
        return this.props.value.type === value.type;
    }

    update(value) {
        if (value.type && !this.isFixedPeriod(value.type)) {
            this.props.update({ type: "relative", period: value.type });
            return;
        }
        switch (value.type) {
            case "range": {
                const { from, to } = this.selectedValues.range;
                if (from && to) {
                    // Ensure 'to' is after 'from'
                    if (DateTime.fromISO(from) > DateTime.fromISO(to)) {
                        this.selectedValues.range.to = from;
                        this.selectedValues.range.from = to;
                    }
                }
                this.props.update(this.selectedValues.range);
                break;
            }
            case undefined:
                this.props.update(undefined);
                break;
            default:
                this.props.update(this.selectedValues[value.type]);
                break;
        }
    }

    dateFrom() {
        return this.selectedValues.range.from
            ? DateTime.fromISO(this.selectedValues.range.from)
            : undefined;
    }

    dateTo() {
        return this.selectedValues.range.to
            ? DateTime.fromISO(this.selectedValues.range.to)
            : undefined;
    }

    setDateFrom(date) {
        this.selectedValues.range.from = date ? date.toISODate() : "";
        this.update(this.selectedValues.range);
    }
    setDateTo(date) {
        this.selectedValues.range.to = date ? date.toISODate() : "";
        this.update(this.selectedValues.range);
    }

    getDescription(type) {
        return dateFilterValueToString(this.selectedValues[type], this.props.model.getters);
    }

    selectPrevious(type) {
        this.selectedValues[type] = getPreviousDateFilterValue(this.selectedValues[type]);
    }

    selectNext(type) {
        this.selectedValues[type] = getNextDateFilterValue(this.selectedValues[type]);
    }

    isFixedPeriod(type) {
        if (!type) {
            return false;
        }
        return globalFilterDateRegistry.get(type).isFixedPeriod;
    }
}
