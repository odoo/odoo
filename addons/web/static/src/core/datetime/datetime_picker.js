import { Component, onWillRender, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import {
    MAX_VALID_DATE,
    MIN_VALID_DATE,
    clampDate,
    is24HourFormat,
    isInRange,
    isMeridiemFormat,
    today,
} from "../l10n/dates";
import { localization } from "../l10n/localization";
import { ensureArray } from "../utils/arrays";

const { DateTime, Info } = luxon;

/**
 * @typedef DateItem
 * @property {string} id
 * @property {boolean} includesToday
 * @property {boolean} isOutOfRange
 * @property {boolean} isValid
 * @property {string} label
 * @property {DateRange} range
 * @property {string} extraClass
 *
 * @typedef {"today" | NullableDateTime} DateLimit
 *
 * @typedef {[DateTime, DateTime]} DateRange
 *
 * @typedef {luxon.DateTime} DateTime
 *
 * @typedef DateTimePickerProps
 * @property {number} [focusedDateIndex=0]
 * @property {boolean} [showWeekNumbers]
 * @property {DaysOfWeekFormat} [daysOfWeekFormat="short"]
 * @property {DateLimit} [maxDate]
 * @property {PrecisionLevel} [maxPrecision="decades"]
 * @property {DateLimit} [minDate]
 * @property {PrecisionLevel} [minPrecision="days"]
 * @property {(value: DateTime) => any} [onSelect]
 * @property {boolean} [range]
 * @property {number} [rounding=5] the rounding in minutes, pass 0 to show seconds, pass 1 to avoid
 *  rounding minutes without displaying seconds.
 * @property {{ buttons?: any }} [slots]
 * @property {"date" | "datetime"} [type]
 * @property {NullableDateTime | NullableDateRange} [value]
 * @property {(date: DateTime) => boolean} [isDateValid]
 * @property {(date: DateTime) => string} [dayCellClass]
 *
 * @typedef {DateItem | MonthItem} Item
 *
 * @typedef MonthItem
 * @property {[string, string][]} daysOfWeek
 * @property {string} id
 * @property {number} number
 * @property {WeekItem[]} weeks
 *
 * @typedef {import("@web/core/l10n/dates").NullableDateTime} NullableDateTime
 *
 * @typedef {import("@web/core/l10n/dates").NullableDateRange} NullableDateRange
 *
 * @typedef PrecisionInfo
 * @property {(date: DateTime, params: Partial<DateTimePickerProps>) => string} getTitle
 * @property {(date: DateTime, params: Partial<DateTimePickerProps>) => Item[]} getItems
 * @property {string} mainTitle
 * @property {string} nextTitle
 * @property {string} prevTitle
 * @property {Record<string, number>} step
 *
 * @typedef {"days" | "months" | "years" | "decades"} PrecisionLevel
 *
 * @typedef {"short" | "narrow"} DaysOfWeekFormat
 *
 * @typedef WeekItem
 * @property {DateItem[]} days
 * @property {number} number
 */

/**
 * @param {NullableDateTime} date1
 * @param {NullableDateTime} date2
 */
const earliest = (date1, date2) => (date1 < date2 ? date1 : date2);

/**
 * @param {DateTime} date
 */
const getStartOfDecade = (date) => Math.floor(date.year / 10) * 10;

/**
 * @param {DateTime} date
 */
const getStartOfCentury = (date) => Math.floor(date.year / 100) * 100;

/**
 * @param {DateTime} date
 */
const getStartOfWeek = (date) => {
    const { weekStart } = localization;
    return date.set({ weekday: date.weekday < weekStart ? weekStart - 7 : weekStart });
};

/**
 * @param {NullableDateTime} date1
 * @param {NullableDateTime} date2
 */
const latest = (date1, date2) => (date1 > date2 ? date1 : date2);

/**
 * @param {number} min
 * @param {number} max
 */
const numberRange = (min, max) => [...Array(max - min)].map((_, i) => i + min);

/**
 * @param {NullableDateTime | "today"} value
 * @param {NullableDateTime | "today"} defaultValue
 */
const parseLimitDate = (value, defaultValue) =>
    clampDate(value === "today" ? today() : value || defaultValue, MIN_VALID_DATE, MAX_VALID_DATE);

/**
 * @param {Object} params
 * @param {boolean} [params.isOutOfRange=false]
 * @param {boolean} [params.isValid=true]
 * @param {keyof DateTime} params.label
 * @param {string} [params.extraClass]
 * @param {[DateTime, DateTime]} params.range
 * @returns {DateItem}
 */
const toDateItem = ({ isOutOfRange = false, isValid = true, label, range, extraClass }) => ({
    id: range[0].toISODate(),
    includesToday: isInRange(today(), range),
    isOutOfRange,
    isValid,
    label: String(range[0][label]),
    range,
    extraClass,
});

/**
 * @param {DateItem[]} weekDayItems
 * @returns {WeekItem}
 */
const toWeekItem = (weekDayItems) => ({
    number: weekDayItems[3].range[0].weekNumber,
    days: weekDayItems,
});

// Time constants
const HOURS = numberRange(0, 24).map((hour) => [hour, String(hour)]);
const MINUTES = numberRange(0, 60).map((minute) => [minute, String(minute || 0).padStart(2, "0")]);
const SECONDS = [...MINUTES];
const MERIDIEMS = ["AM", "PM"];

/**
 * Precision levels
 * @type {Map<PrecisionLevel, PrecisionInfo>}
 */
const PRECISION_LEVELS = new Map()
    .set("days", {
        mainTitle: _t("Select month"),
        nextTitle: _t("Next month"),
        prevTitle: _t("Previous month"),
        step: { month: 1 },
        getTitle: (date, { additionalMonth }) => {
            const titles = [`${date.monthLong} ${date.year}`];
            if (additionalMonth) {
                const next = date.plus({ month: 1 });
                titles.push(`${next.monthLong} ${next.year}`);
            }
            return titles;
        },
        getItems: (
            date,
            { additionalMonth, maxDate, minDate, showWeekNumbers, isDateValid, dayCellClass }
        ) => {
            const startDates = [date];
            if (additionalMonth) {
                startDates.push(date.plus({ month: 1 }));
            }
            return startDates.map((date, i) => {
                const monthRange = [date.startOf("month"), date.endOf("month")];
                /** @type {WeekItem[]} */
                const weeks = [];

                // Generate 6 weeks for current month
                let startOfNextWeek = getStartOfWeek(monthRange[0]);
                for (let w = 0; w < 6; w++) {
                    const weekDayItems = [];
                    // Generate all days of the week
                    for (let d = 0; d < 7; d++) {
                        const day = startOfNextWeek.plus({ day: d });
                        const range = [day, day.endOf("day")];
                        const dayItem = toDateItem({
                            isOutOfRange: !isInRange(day, monthRange),
                            isValid: isInRange(range, [minDate, maxDate]) && isDateValid?.(day),
                            label: "day",
                            range,
                            extraClass: dayCellClass?.(day) || "",
                        });
                        weekDayItems.push(dayItem);
                        if (d === 6) {
                            startOfNextWeek = day.plus({ day: 1 });
                        }
                    }
                    weeks.push(toWeekItem(weekDayItems));
                }

                // Generate days of week labels
                const daysOfWeek = weeks[0].days.map((d) => [
                    d.range[0].weekdayShort,
                    d.range[0].weekdayLong,
                    Info.weekdays("narrow", { locale: d.range[0].locale })[d.range[0].weekday - 1],
                ]);
                if (showWeekNumbers) {
                    daysOfWeek.unshift(["#", _t("Week numbers"), "#"]);
                }

                return {
                    id: `__month__${i}`,
                    number: monthRange[0].month,
                    daysOfWeek,
                    weeks,
                };
            });
        },
    })
    .set("months", {
        mainTitle: _t("Select year"),
        nextTitle: _t("Next year"),
        prevTitle: _t("Previous year"),
        step: { year: 1 },
        getTitle: (date) => String(date.year),
        getItems: (date, { maxDate, minDate }) => {
            const startOfYear = date.startOf("year");
            return numberRange(0, 12).map((i) => {
                const startOfMonth = startOfYear.plus({ month: i });
                const range = [startOfMonth, startOfMonth.endOf("month")];
                return toDateItem({
                    isValid: isInRange(range, [minDate, maxDate]),
                    label: "monthShort",
                    range,
                });
            });
        },
    })
    .set("years", {
        mainTitle: _t("Select decade"),
        nextTitle: _t("Next decade"),
        prevTitle: _t("Previous decade"),
        step: { year: 10 },
        getTitle: (date) => `${getStartOfDecade(date) - 1} - ${getStartOfDecade(date) + 10}`,
        getItems: (date, { maxDate, minDate }) => {
            const startOfDecade = date.startOf("year").set({ year: getStartOfDecade(date) });
            return numberRange(-GRID_MARGIN, GRID_COUNT + GRID_MARGIN).map((i) => {
                const startOfYear = startOfDecade.plus({ year: i });
                const range = [startOfYear, startOfYear.endOf("year")];
                return toDateItem({
                    isOutOfRange: i < 0 || i >= GRID_COUNT,
                    isValid: isInRange(range, [minDate, maxDate]),
                    label: "year",
                    range,
                });
            });
        },
    })
    .set("decades", {
        mainTitle: _t("Select century"),
        nextTitle: _t("Next century"),
        prevTitle: _t("Previous century"),
        step: { year: 100 },
        getTitle: (date) => `${getStartOfCentury(date) - 10} - ${getStartOfCentury(date) + 100}`,
        getItems: (date, { maxDate, minDate }) => {
            const startOfCentury = date.startOf("year").set({ year: getStartOfCentury(date) });
            return numberRange(-GRID_MARGIN, GRID_COUNT + GRID_MARGIN).map((i) => {
                const startOfDecade = startOfCentury.plus({ year: i * 10 });
                const range = [startOfDecade, startOfDecade.plus({ year: 10, millisecond: -1 })];
                return toDateItem({
                    label: "year",
                    isOutOfRange: i < 0 || i >= GRID_COUNT,
                    isValid: isInRange(range, [minDate, maxDate]),
                    range,
                });
            });
        },
    });

// Other constants
const GRID_COUNT = 10;
const GRID_MARGIN = 1;
const NULLABLE_DATETIME_PROPERTY = [DateTime, { value: false }, { value: null }];

/** @extends {Component<DateTimePickerProps>} */
export class DateTimePicker extends Component {
    static props = {
        focusedDateIndex: { type: Number, optional: true },
        showWeekNumbers: { type: Boolean, optional: true },
        daysOfWeekFormat: { type: String, optional: true },
        maxDate: { type: [NULLABLE_DATETIME_PROPERTY, { value: "today" }], optional: true },
        maxPrecision: {
            type: [...PRECISION_LEVELS.keys()].map((value) => ({ value })),
            optional: true,
        },
        minDate: { type: [NULLABLE_DATETIME_PROPERTY, { value: "today" }], optional: true },
        minPrecision: {
            type: [...PRECISION_LEVELS.keys()].map((value) => ({ value })),
            optional: true,
        },
        onSelect: { type: Function, optional: true },
        range: { type: Boolean, optional: true },
        rounding: { type: Number, optional: true },
        slots: {
            type: Object,
            shape: {
                bottom_left: { type: Object, optional: true },
                buttons: { type: Object, optional: true },
            },
            optional: true,
        },
        type: { type: [{ value: "date" }, { value: "datetime" }], optional: true },
        value: {
            type: [
                NULLABLE_DATETIME_PROPERTY,
                { type: Array, element: NULLABLE_DATETIME_PROPERTY },
            ],
            optional: true,
        },
        isDateValid: { type: Function, optional: true },
        dayCellClass: { type: Function, optional: true },
        tz: { type: String, optional: true },
    };

    static defaultProps = {
        focusedDateIndex: 0,
        daysOfWeekFormat: "short",
        maxPrecision: "decades",
        minPrecision: "days",
        rounding: 5,
        type: "datetime",
    };

    static template = "web.DateTimePicker";

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    get activePrecisionLevel() {
        return PRECISION_LEVELS.get(this.state.precision);
    }

    get isLastPrecisionLevel() {
        return (
            this.allowedPrecisionLevels.indexOf(this.state.precision) ===
            this.allowedPrecisionLevels.length - 1
        );
    }

    get titles() {
        return ensureArray(this.title);
    }

    //-------------------------------------------------------------------------
    // Lifecycle
    //-------------------------------------------------------------------------

    setup() {
        this.availableHours = HOURS;
        this.availableMinutes = MINUTES;
        /** @type {PrecisionLevel[]} */
        this.allowedPrecisionLevels = [];
        /** @type {Item[]} */
        this.items = [];
        this.title = "";
        this.shouldAdjustFocusDate = false;

        this.state = useState({
            /** @type {DateTime | null} */
            focusDate: null,
            /** @type {DateTime | null} */
            hoveredDate: null,
            /** @type {[number, number, number][]} */
            timeValues: [],
            /** @type {PrecisionLevel} */
            precision: this.props.minPrecision,
        });

        this.onPropsUpdated(this.props);
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));

        onWillRender(() => this.onWillRender());
    }

    /**
     * @param {DateTimePickerProps} props
     */
    onPropsUpdated(props) {
        /** @type {[NullableDateTime] | NullableDateRange} */
        this.values = ensureArray(props.value).map((value) =>
            value && !value.isValid ? null : value
        );
        this.availableHours = HOURS;
        this.availableMinutes = MINUTES.filter((minute) => !(minute[0] % props.rounding));
        this.availableSeconds = props.rounding ? [] : SECONDS;
        this.allowedPrecisionLevels = this.filterPrecisionLevels(
            props.minPrecision,
            props.maxPrecision
        );

        this.additionalMonth = props.range && !this.env.isSmall;
        this.maxDate = parseLimitDate(props.maxDate, MAX_VALID_DATE);
        this.minDate = parseLimitDate(props.minDate, MIN_VALID_DATE);
        if (this.props.type === "date") {
            this.maxDate = this.maxDate.endOf("day");
            this.minDate = this.minDate.startOf("day");
        }

        if (this.maxDate < this.minDate) {
            throw new Error(`DateTimePicker error: given "maxDate" comes before "minDate".`);
        }

        const timeValues = this.values.map((val, index) => [
            index === 1 && !this.values[1]
                ? (val || DateTime.local()).hour + 1
                : (val || DateTime.local()).hour,
            val?.minute || 0,
            val?.second || 0,
        ]);
        if (props.range) {
            this.state.timeValues = timeValues;
        } else {
            this.state.timeValues = [];
            this.state.timeValues[props.focusedDateIndex] = timeValues[props.focusedDateIndex];
        }

        this.shouldAdjustFocusDate = !props.range;
        this.adjustFocus(this.values, props.focusedDateIndex);
        this.handle12HourSystem();
        this.state.timeValues = this.state.timeValues.map((timeValue) => timeValue.map(String));
    }

    onWillRender() {
        const { hoveredDate } = this.state;
        const precision = this.activePrecisionLevel;
        const getterParams = {
            additionalMonth: this.additionalMonth,
            maxDate: this.maxDate,
            minDate: this.minDate,
            showWeekNumbers: this.props.showWeekNumbers ?? !this.props.range,
            isDateValid: this.props.isDateValid,
            dayCellClass: this.props.dayCellClass,
        };
        const referenceDate = this.state.focusDate;
        this.title = precision.getTitle(referenceDate, getterParams);
        this.items = precision.getItems(referenceDate, getterParams);

        /** Selected Range: current values with hovered date applied */
        this.selectedRange = [...this.values];
        /** Highlighted Range: union of current values and selected range */
        this.highlightedRange = [...this.values];

        // Apply hovered date to selected range
        if (hoveredDate) {
            [this.selectedRange] = this.applyValueAtIndex(hoveredDate, this.props.focusedDateIndex);
            if (this.props.range && this.selectedRange.every(Boolean)) {
                this.highlightedRange = [
                    earliest(this.selectedRange[0], this.values[0]),
                    latest(this.selectedRange[1], this.values[1]),
                ];
            }
        }
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    /**
     * @param {NullableDateTime[]} values
     * @param {number} focusedDateIndex
     */
    adjustFocus(values, focusedDateIndex) {
        if (!this.shouldAdjustFocusDate && this.state.focusDate) {
            return;
        }

        let dateToFocus =
            values[focusedDateIndex] || values[focusedDateIndex === 1 ? 0 : 1] || today();

        if (
            this.additionalMonth &&
            focusedDateIndex === 1 &&
            values[0] &&
            values[1] &&
            values[0].month !== values[1].month
        ) {
            dateToFocus = dateToFocus.minus({ month: 1 });
        }

        this.shouldAdjustFocusDate = false;
        this.state.focusDate = this.clamp(dateToFocus.startOf("month"));
    }

    /**
     * @param {NullableDateTime} value
     * @param {number} valueIndex
     * @returns {[NullableDateRange, number]}
     */
    applyValueAtIndex(value, valueIndex) {
        const result = [...this.values];
        if (this.props.range) {
            if (
                (result[0] && value.endOf("day") < result[0].startOf("day")) ||
                (result[1] && !result[0])
            ) {
                valueIndex = 0;
            } else if (
                (result[1] && result[1].endOf("day") < value.startOf("day")) ||
                (result[0] && !result[1])
            ) {
                valueIndex = 1;
            }
        }
        result[valueIndex] = value;
        return [result, valueIndex];
    }

    /**
     * @param {DateTime} value
     */
    clamp(value) {
        return clampDate(value, this.minDate, this.maxDate);
    }

    /**
     * @param {PrecisionLevel} minPrecision
     * @param {PrecisionLevel} maxPrecision
     */
    filterPrecisionLevels(minPrecision, maxPrecision) {
        const levels = [...PRECISION_LEVELS.keys()];
        return levels.slice(levels.indexOf(minPrecision), levels.indexOf(maxPrecision) + 1);
    }

    /**
     * Returns various flags indicating what ranges the current date item belongs
     * to. Note that these ranges are computed differently according to the current
     * value mode (range or single date). This is done to simplify CSS selectors.
     * - Selected Range:
     *      > range: current values with hovered date applied
     *      > single date: just the hovered date
     * - Highlighted Range:
     *      > range: union of selection range and current values
     *      > single date: just the current value
     * - Current Range (range only):
     *      > range: current start date or current end date.
     * @param {DateItem} item
     */
    getActiveRangeInfo({ isOutOfRange, range }) {
        const result = {
            isSelected: !isOutOfRange && isInRange(this.selectedRange, range),
            isSelectStart: false,
            isSelectEnd: false,
            isHighlighted: !isOutOfRange && isInRange(this.highlightedRange, range),
            isHighlightStart: false,
            isHighlightEnd: false,
            isCurrent: false,
        };

        if (this.props.range) {
            if (result.isSelected) {
                const [selectStart, selectEnd] = this.selectedRange;
                result.isSelectStart = !selectStart || isInRange(selectStart, range);
                result.isSelectEnd = !selectEnd || isInRange(selectEnd, range);
            }
            if (result.isHighlighted) {
                const [currentStart, currentEnd] = this.highlightedRange;
                result.isHighlightStart = !currentStart || isInRange(currentStart, range);
                result.isHighlightEnd = !currentEnd || isInRange(currentEnd, range);
            }
            result.isCurrent =
                !isOutOfRange &&
                (isInRange(this.values[0], range) || isInRange(this.values[1], range));
        } else {
            result.isSelectStart = result.isSelectEnd = result.isSelected;
            result.isHighlightStart = result.isHighlightEnd = result.isHighlighted;
        }

        return result;
    }

    getTimeValues(valueIndex) {
        let [hour, minute, second] = this.state.timeValues[valueIndex].map(Number);
        if (
            this.is12HourFormat &&
            this.meridiems &&
            this.state.timeValues[valueIndex][3] === "PM"
        ) {
            hour += 12;
        }
        return [hour, minute, second];
    }

    handle12HourSystem() {
        if (isMeridiemFormat()) {
            this.meridiems = MERIDIEMS.map((m) => [m, m]);
            for (const timeValues of this.state.timeValues) {
                if (timeValues) {
                    timeValues.push(MERIDIEMS[Math.floor(timeValues[0] / 12) || 0]);
                }
            }
        }
        this.is12HourFormat = !is24HourFormat();
        if (this.is12HourFormat) {
            this.availableHours = [[0, HOURS[12][1]], ...HOURS.slice(1, 12)];
            for (const timeValues of this.state.timeValues) {
                if (timeValues) {
                    timeValues[0] %= 12;
                }
            }
        }
    }

    /**
     * @param {DateItem} item
     */
    isSelectedDate({ range }) {
        return this.values.some((value) => isInRange(value, range));
    }

    /**
     * Goes to the next panel (e.g. next month if precision is "days").
     * If an event is given it will be prevented.
     * @param {PointerEvent} ev
     */
    next(ev) {
        ev.preventDefault();
        const { step } = this.activePrecisionLevel;
        this.state.focusDate = this.clamp(this.state.focusDate.plus(step));
    }

    /**
     * Goes to the previous panel (e.g. previous month if precision is "days").
     * If an event is given it will be prevented.
     * @param {PointerEvent} ev
     */
    previous(ev) {
        ev.preventDefault();
        const { step } = this.activePrecisionLevel;
        this.state.focusDate = this.clamp(this.state.focusDate.minus(step));
    }

    /**
     * Happens when an hour or a minute (or AM/PM if can apply) is selected.
     * @param {number} valueIndex
     */
    selectTime(valueIndex) {
        const value = this.values[valueIndex] || today();
        this.validateAndSelect(value, valueIndex);
    }

    /**
     * @param {DateTime} value
     * @param {number} valueIndex
     */
    validateAndSelect(value, valueIndex) {
        if (!this.props.onSelect) {
            // No onSelect handler
            return false;
        }
        const [result, finalIndex] = this.applyValueAtIndex(value, valueIndex);
        if (this.props.type === "datetime") {
            // Adjusts result according to the current time values
            const [hour, minute, second] = this.getTimeValues(finalIndex);
            result[finalIndex] = result[finalIndex].set({ hour, minute, second });
        }
        if (!isInRange(result[finalIndex], [this.minDate, this.maxDate])) {
            // Date is outside range defined by min and max dates
            return false;
        }
        this.props.onSelect(result.length === 2 ? result : result[0]);
        return true;
    }

    /**
     * Returns whether the zoom has occurred
     * @param {DateTime} date
     */
    zoomIn(date) {
        const index = this.allowedPrecisionLevels.indexOf(this.state.precision) - 1;
        if (index in this.allowedPrecisionLevels) {
            this.state.focusDate = this.clamp(date);
            this.state.precision = this.allowedPrecisionLevels[index];
            return true;
        }
        return false;
    }

    /**
     * Returns whether the zoom has occurred
     */
    zoomOut() {
        const index = this.allowedPrecisionLevels.indexOf(this.state.precision) + 1;
        if (index in this.allowedPrecisionLevels) {
            this.state.precision = this.allowedPrecisionLevels[index];
            return true;
        }
        return false;
    }

    /**
     * Happens when a date item is selected:
     * - first tries to zoom in on the item
     * - if could not zoom in: date is considered as final value and triggers a hard select
     * @param {DateItem} dateItem
     */
    zoomOrSelect(dateItem) {
        if (!dateItem.isValid) {
            // Invalid item
            return;
        }
        if (this.zoomIn(dateItem.range[0])) {
            // Zoom was successful
            return;
        }
        const [value] = dateItem.range;
        const valueIndex = this.props.focusedDateIndex;
        const isValid = this.validateAndSelect(value, valueIndex);
        this.shouldAdjustFocusDate = isValid && !this.props.range;
    }
}
