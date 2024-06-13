import { Component, useState } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { formatDate, getLocalWeekNumber, getStartOfLocalWeek } from "@web/core/l10n/dates";
import { pick } from "@web/core/utils/objects";
import { debounce } from "@web/core/utils/timing";

const { DateTime } = luxon;

function diffColumn(col1, col2, unit) {
    return col2.diff(col1, unit).values[`${unit}s`];
}

function getRangeFromDate(rangeId, date) {
    const startDate = localStartOf(date, rangeId);
    const stopDate = startDate.plus({ [rangeId]: 1 }).minus({ day: 1 });
    return { focusDate: date, startDate, stopDate, rangeId };
}

function localStartOf(date, unit) {
    return unit === "week" ? getStartOfLocalWeek(date) : date.startOf(unit);
}

const KEYS = ["startDate", "stopDate", "rangeId", "focusDate"];

export class ViewRangeSelector extends Component {
    static components = {
        Dropdown,
        DropdownItem,
    };
    static template = "web.ViewRangeSelector";
    static props = {
        dropdownClass: { type: String, optional: true },
        focusDate: DateTime,
        startDate: DateTime,
        stopDate: DateTime,
        rangeId: String,
        ranges: Array,
        update: Function,
    };

    setup() {
        this.update = debounce(() => this.props.update({ ...pick(this.state, ...KEYS) }), 500);

        this.state = useState({ ...pick(this.props, ...KEYS) });

        /** @type {Object} */
        this.pickerValues = useState({
            startDate: this.props.startDate,
            stopDate: this.props.stopDate,
        });

        const getPickerProps = (key) => ({ type: "date", value: this.pickerValues[key] });
        this.startPicker = useDateTimePicker({
            target: "start-picker",
            onApply: (date) => {
                this.pickerValues.startDate = date;
                if (this.pickerValues.stopDate < date) {
                    this.pickerValues.stopDate = date;
                } else if (date.plus({ year: 10, day: -1 }) < this.pickerValues.stopDate) {
                    this.pickerValues.stopDate = date.plus({ year: 10, day: -1 });
                }
            },
            get pickerProps() {
                return getPickerProps("startDate");
            },
            ensureVisibility: () => false,
        });
        this.stopPicker = useDateTimePicker({
            target: "stop-picker",
            onApply: (date) => {
                this.pickerValues.stopDate = date;
                if (date < this.pickerValues.startDate) {
                    this.pickerValues.startDate = date;
                } else if (this.pickerValues.startDate.plus({ year: 10, day: -1 }) < date) {
                    this.pickerValues.startDate = date.minus({ year: 10, day: -1 });
                }
            },
            get pickerProps() {
                return getPickerProps("stopDate");
            },
            ensureVisibility: () => false,
        });

        this.dropdownState = useDropdownState();
    }

    get dateDescription() {
        const { focusDate, rangeId } = this.state;
        switch (rangeId) {
            case "day":
                return formatDate(focusDate);
            case "week":
                return focusDate.toFormat(`'W${getLocalWeekNumber(focusDate)}' yyyy`);
            case "month":
                return focusDate.toFormat(this.env.isSmall ? "MMM yyyy" : "MMMM yyyy");
            case "quarter":
                return focusDate.toFormat(`Qq yyyy`);
            default:
                return focusDate.toFormat("yyyy");
        }
    }

    getFormattedDate(date) {
        return formatDate(date);
    }

    isSelected(rangeId) {
        if (rangeId === "custom") {
            return (
                this.state.rangeId === rangeId ||
                !localStartOf(this.state.focusDate, this.state.rangeId).equals(
                    localStartOf(DateTime.now(), this.state.rangeId)
                )
            );
        }
        return (
            this.state.rangeId === rangeId &&
            localStartOf(this.state.focusDate, rangeId).equals(
                localStartOf(DateTime.now(), rangeId)
            )
        );
    }

    onApply() {
        this.state.startDate = this.pickerValues.startDate;
        this.state.stopDate = this.pickerValues.stopDate;
        this.state.rangeId = "custom";
        this.update();
        this.dropdownState.close();
    }

    selectRange(direction) {
        const sign = direction === "next" ? 1 : -1;
        const { focusDate, rangeId, startDate, stopDate } = this.state;
        if (rangeId === "custom") {
            const diff = diffColumn(startDate, stopDate, "day") + 1;
            this.state.focusDate = focusDate.plus({ day: sign * diff });
            this.state.startDate = startDate.plus({ day: sign * diff });
            this.state.stopDate = stopDate.plus({ day: sign * diff });
        } else {
            Object.assign(
                this.state,
                getRangeFromDate(rangeId, focusDate.plus({ [rangeId]: sign }))
            );
        }
        this.updatePickerValues();
        this.update();
    }

    selectRangeId(rangeId) {
        Object.assign(this.state, getRangeFromDate(rangeId, DateTime.now().startOf("day")));
        this.updatePickerValues();
        this.update();
    }

    updatePickerValues() {
        this.pickerValues.startDate = this.state.startDate;
        this.pickerValues.stopDate = this.state.stopDate;
    }
}
