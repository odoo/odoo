import { Component, signal, t, useOnChange, useProps } from "@odoo/owl";
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

    props = useProps({
        value: t.object().optional(),
        update: t.function(),
        model: t.object(),
    });

    selectedValues = signal.Object(this._getDefaultSelectedValues());

    setup() {
        useOnChange(
            () => [this.props.value],
            (value) => this._applyCurrentValueToSelectedValues(value)
        );
    }

    /**
     * Updates the selected values based on the current value.
     * This method is called whenever the `value` prop changes.
     */
    _applyCurrentValueToSelectedValues(value) {
        this.selectedValues().range = this._getRange(value);
        if (value?.type) {
            const filterType = value.type === "relative" ? value.period : value.type;
            if (this.isFixedPeriod(filterType)) {
                this.selectedValues()[value.type] = { ...value };
            }
        }
    }

    /**
     * Computes the default selected values based on the current date.
     */
    _getDefaultSelectedValues() {
        const now = DateTime.local();
        const fixedPeriodsTypes = getDateGlobalFilterTypes().filter(
            (type) => globalFilterDateRegistry.get(type).isFixedPeriod
        );

        const selectedValues = {};
        for (const type of fixedPeriodsTypes) {
            selectedValues[type] = globalFilterDateRegistry.get(type).getCurrentFixedPeriod(now);
        }
        return selectedValues;
    }

    _getRange(value) {
        const now = DateTime.local();
        const { from, to } = getDateRange(value, 0, now, this.props.model.getters);
        return {
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
        if (value.type === undefined) {
            this.props.update(undefined);
            return;
        }
        const selectedValue = this.selectedValues()[value.type];
        const { from, to } = selectedValue;
        // Ensure 'to' is after 'from'
        if (from && to && DateTime.fromISO(from) > DateTime.fromISO(to)) {
            selectedValue.from = to;
            selectedValue.to = from;
        }
        // Copy: the model must not hold (nor share) the reactive selected value
        this.props.update({ ...selectedValue });
    }

    dateFrom() {
        const { from } = this.selectedValues().range;
        return from ? DateTime.fromISO(from) : undefined;
    }

    dateTo() {
        const { to } = this.selectedValues().range;
        return to ? DateTime.fromISO(to) : undefined;
    }

    setDateFrom(date) {
        const { range } = this.selectedValues();
        range.from = date ? date.toISODate() : "";
        this.update(range);
    }
    setDateTo(date) {
        const { range } = this.selectedValues();
        range.to = date ? date.toISODate() : "";
        this.update(range);
    }

    getDescription(type) {
        return dateFilterValueToString(this.selectedValues()[type], this.props.model.getters);
    }

    selectPrevious(type) {
        this.selectedValues()[type] = getPreviousDateFilterValue(this.selectedValues()[type]);
    }

    selectNext(type) {
        this.selectedValues()[type] = getNextDateFilterValue(this.selectedValues()[type]);
    }

    isFixedPeriod(type) {
        if (!type) {
            return false;
        }
        return globalFilterDateRegistry.get(type).isFixedPeriod;
    }
}
