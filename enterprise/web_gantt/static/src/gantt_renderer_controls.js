import { Component, useState } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { formatDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { pick } from "@web/core/utils/objects";
import { debounce } from "@web/core/utils/timing";
import {
    diffColumn,
    getRangeFromDate,
    localStartOf,
    useGanttResponsivePopover,
} from "./gantt_helpers";

const { DateTime } = luxon;

const KEYS = ["startDate", "stopDate", "rangeId", "focusDate"];

export class GanttRendererControls extends Component {
    static template = "web_gantt.GanttRendererControls";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = ["model", "displayExpandCollapseButtons", "focusToday", "getCurrentFocusDate"];
    static toolbarContentTemplate = "web_gantt.GanttRendererControls.ToolbarContent";
    static rangeMenuTemplate = "web_gantt.GanttRendererControls.RangeMenu";

    setup() {
        this.model = this.props.model;
        this.updateMetaData = debounce(() => this.model.fetchData(this.makeParams()), 500);

        const { metaData } = this.model;
        this.state = useState({
            scaleIndex: this.getScaleIndex(metaData.scale.id),
            ...pick(metaData, ...KEYS),
        });
        this.pickerValues = useState({
            startDate: metaData.startDate,
            stopDate: metaData.stopDate,
        });
        this.scalesRange = { min: 0, max: Object.keys(metaData.scales).length - 1 };

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
            createPopover: (...args) => useGanttResponsivePopover(_t("Gantt start date"), ...args),
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
            createPopover: (...args) => useGanttResponsivePopover(_t("Gantt stop date"), ...args),
            ensureVisibility: () => false,
        });

        this.dropdownState = useDropdownState();
    }

    get dateDescription() {
        const { focusDate, rangeId } = this.state;
        switch (rangeId) {
            case "quarter":
                return focusDate.toFormat(`Qq yyyy`);
            case "day":
                return formatDate(focusDate);
            default:
                return this.model.metaData.ranges[rangeId].groupHeaderFormatter(
                    focusDate,
                    this.env
                );
        }
    }

    get formattedDateRange() {
        return _t("From: %(from_date)s to: %(to_date)s", {
            from_date: formatDate(this.state.startDate),
            to_date: formatDate(this.state.stopDate),
        });
    }

    getFormattedDate(date) {
        return formatDate(date);
    }

    getScaleIdFromIndex(index) {
        const keys = Object.keys(this.model.metaData.scales);
        return keys[keys.length - 1 - index];
    }

    getScaleIndex(scaleId) {
        const keys = Object.keys(this.model.metaData.scales);
        return keys.length - 1 - keys.findIndex((id) => id === scaleId);
    }

    getScaleIndexFromRangeId(rangeId) {
        const { ranges } = this.model.metaData;
        const scaleId = ranges[rangeId].scaleId;
        return this.getScaleIndex(scaleId);
    }

    /**
     * @param {1|-1} inc
     */
    incrementScale(inc) {
        if (
            inc === 1
                ? this.state.scaleIndex < this.scalesRange.max
                : this.scalesRange.min < this.state.scaleIndex
        ) {
            this.state.scaleIndex += inc;
            this.updateMetaData();
        }
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

    makeParams() {
        return {
            currentFocusDate: this.props.getCurrentFocusDate(),
            scaleId: this.getScaleIdFromIndex(this.state.scaleIndex),
            ...pick(this.state, ...KEYS),
        };
    }

    onApply() {
        this.state.startDate = this.pickerValues.startDate;
        this.state.stopDate = this.pickerValues.stopDate;
        this.state.rangeId = "custom";
        this.updateMetaData();
        this.dropdownState.close();
    }

    onTodayClicked() {
        const success = this.props.focusToday();
        if (success) {
            return;
        }
        this.state.focusDate = DateTime.local().startOf("day");
        if (this.state.rangeId === "custom") {
            const diff = diffColumn(this.state.startDate, this.state.stopDate, "day");
            const n = Math.floor(diff / 2);
            const m = diff - n;
            this.state.startDate = this.state.focusDate.minus({ day: n });
            this.state.stopDate = this.state.focusDate.plus({ day: m - 1 });
        } else {
            this.state.startDate = this.state.focusDate.startOf(this.state.rangeId);
            this.state.stopDate = this.state.focusDate.endOf(this.state.rangeId).startOf("day");
        }
        this.updatePickerValues();
        this.updateMetaData();
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
        this.updateMetaData();
    }

    selectRangeId(rangeId) {
        Object.assign(this.state, getRangeFromDate(rangeId, DateTime.now().startOf("day")));
        this.state.scaleIndex = this.getScaleIndexFromRangeId(rangeId);
        this.updatePickerValues();
        this.updateMetaData();
    }

    selectScale(index) {
        this.state.scaleIndex = Number(index);
        this.updateMetaData();
    }

    updatePickerValues() {
        this.pickerValues.startDate = this.state.startDate;
        this.pickerValues.stopDate = this.state.stopDate;
    }
}
