/** @odoo-module **/

import {
    Component,
    onWillRender,
    onWillUpdateProps,
    useExternalListener,
    useState,
} from "@odoo/owl";
import { _lt } from "@web/core/l10n/translation";
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

/**
 * @typedef DateItem
 * @property {string} id
 * @property {boolean} includesToday
 * @property {boolean} isOutOfRange
 * @property {boolean} isInvalid
 * @property {string} label
 * @property {DateRange} range
 *
 * @typedef {"today" | NullableDateTime} DateLimit
 *
 * @typedef {[DateTime, DateTime]} DateRange
 *
 * @typedef {luxon.DateTime} DateTime
 *
 * @typedef DateTimePickerProps
 * @property {number} [focusedDateIndex=0]
 * @property {DateLimit} [maxDate]
 * @property {PrecisionLevel} [maxPrecision="decades"]
 * @property {DateLimit} [minDate]
 * @property {PrecisionLevel} [minPrecision="days"]
 * @property {(value: DateTime) => any} [onSelect]
 * @property {number} [rounding=5]
 * @property {{ buttons?: any }} [slots]
 * @property {"date" | "datetime"} [type]
 * @property {NullableDateTime | NullableDateRange} value
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
 * @typedef WeekItem
 * @property {DateItem[]} days
 * @property {number} number
 */

const { DateTime } = luxon;

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
 * @param {boolean} [params.isInvalid=false]
 * @param {keyof DateTime} params.label
 * @param {[DateTime, DateTime]} params.range
 * @returns {DateItem}
 */
const toDateItem = ({ isOutOfRange = false, isInvalid = false, label, range }) => ({
    id: range[0].toISODate(),
    includesToday: isInRange(today(), range),
    isOutOfRange,
    isInvalid,
    label: String(range[0][label]),
    range,
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
const MERIDIEMS = ["AM", "PM"];

/**
 * Precision levels
 * @type {Map<PrecisionLevel, PrecisionInfo>}
 */
const PRECISION_LEVELS = new Map()
    .set("days", {
        mainTitle: _lt("Select month"),
        nextTitle: _lt("Next month"),
        prevTitle: _lt("Previous month"),
        step: { month: 1 },
        getTitle: (date, { additionalMonth }) => {
            const titles = [`${date.monthLong} ${date.year}`];
            if (additionalMonth) {
                const next = date.plus({ month: 1 });
                titles.push(`${next.monthLong} ${next.year}`);
            }
            return titles;
        },
        getItems: (date, { additionalMonth, maxDate, minDate, showWeekNumbers }) => {
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
                        const dayItem = toDateItem({
                            isOutOfRange: !isInRange(day, monthRange),
                            isInvalid: !isInRange(day, [minDate, maxDate]),
                            label: "day",
                            range: [day, day.endOf("day")],
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
                ]);
                if (showWeekNumbers) {
                    daysOfWeek.unshift(["#", _lt("Week numbers")]);
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
        mainTitle: _lt("Select year"),
        nextTitle: _lt("Next year"),
        prevTitle: _lt("Previous year"),
        step: { year: 1 },
        getTitle: (date) => String(date.year),
        getItems: (date, { maxDate, minDate }) => {
            const startOfYear = date.startOf("year");
            return numberRange(0, 12).map((i) => {
                const startOfMonth = startOfYear.plus({ month: i });
                return toDateItem({
                    isInvalid: !isInRange(startOfMonth, [minDate, maxDate]),
                    label: "monthShort",
                    range: [startOfMonth, startOfMonth.endOf("month")],
                });
            });
        },
    })
    .set("years", {
        mainTitle: _lt("Select decade"),
        nextTitle: _lt("Next decade"),
        prevTitle: _lt("Previous decade"),
        step: { year: 10 },
        getTitle: (date) => `${getStartOfDecade(date) - 1} - ${getStartOfDecade(date) + 10}`,
        getItems: (date, { maxDate, minDate }) => {
            const startOfDecade = date.startOf("year").set({ year: getStartOfDecade(date) });
            return numberRange(-GRID_MARGIN, GRID_COUNT + GRID_MARGIN).map((i) => {
                const startOfYear = startOfDecade.plus({ year: i });
                return toDateItem({
                    isOutOfRange: i < 0 || i >= GRID_COUNT,
                    isInvalid: !isInRange(startOfYear, [minDate, maxDate]),
                    label: "year",
                    range: [startOfYear, startOfYear.endOf("year")],
                });
            });
        },
    })
    .set("decades", {
        mainTitle: _lt("Select century"),
        nextTitle: _lt("Next century"),
        prevTitle: _lt("Previous century"),
        step: { year: 100 },
        getTitle: (date) => `${getStartOfCentury(date) - 10} - ${getStartOfCentury(date) + 100}`,
        getItems: (date, { maxDate, minDate }) => {
            const startOfCentury = date.startOf("year").set({ year: getStartOfCentury(date) });
            return numberRange(-GRID_MARGIN, GRID_COUNT + GRID_MARGIN).map((i) => {
                const startOfDecade = startOfCentury.plus({ year: i * 10 });
                return toDateItem({
                    label: "year",
                    isOutOfRange: i < 0 || i >= GRID_COUNT,
                    isInvalid: !isInRange(startOfDecade, [minDate, maxDate]),
                    range: [startOfDecade, startOfDecade.plus({ year: 10, millisecond: -1 })],
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
        rounding: { type: Number, optional: true },
        slots: {
            type: Object,
            shape: { buttons: { type: Object, optional: true } },
            optional: true,
        },
        type: { type: [{ value: "date" }, { value: "datetime" }], optional: true },
        value: {
            type: [
                NULLABLE_DATETIME_PROPERTY,
                {
                    type: Array,
                    element: NULLABLE_DATETIME_PROPERTY,
                    validate: (values) => values.length === 2,
                },
            ],
            optional: true,
        },
    };

    static defaultProps = {
        focusedDateIndex: 0,
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

    get isKeynavEnabled() {
        return this.isRange || this.props.type === "datetime";
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
        this.isRange = false;
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

        useExternalListener(
            window,
            "keydown",
            (ev) => this.isKeynavEnabled && this.onWindowKeyDown(ev)
        );
    }

    /**
     * @param {DateTimePickerProps} props
     */
    onPropsUpdated(props) {
        /** @type {[NullableDateTime] | NullableDateRange} */
        this.values = ensureArray(props.value).map((value) =>
            value && !value.isValid ? null : value
        );
        this.isRange = Array.isArray(props.value);
        this.availableHours = HOURS;
        this.availableMinutes = MINUTES.filter((minute) => !(minute[0] % props.rounding));
        this.allowedPrecisionLevels = this.filterPrecisionLevels(
            props.minPrecision,
            props.maxPrecision
        );

        this.additionalMonth = this.isRange && !this.env.isSmall;
        this.maxDate = parseLimitDate(props.maxDate, MAX_VALID_DATE).endOf("day");
        this.minDate = parseLimitDate(props.minDate, MIN_VALID_DATE).startOf("day");

        if (this.maxDate < this.minDate) {
            throw new Error(`DateTimePicker error: given "maxDate" comes before "minDate".`);
        }

        this.state.timeValues = this.values.map((val) => [
            (val || DateTime.local()).hour,
            val?.minute || 0,
            val?.second || 0,
        ]);

        this.adjustFocus(this.values, props.focusedDateIndex);
        this.handle12HourSystem();
    }

    onWillRender() {
        const precision = this.activePrecisionLevel;
        const getterParams = {
            additionalMonth: this.additionalMonth,
            maxDate: this.maxDate,
            minDate: this.minDate,
            showWeekNumbers: !this.isRange,
        };
        const referenceDate = this.state.focusDate;
        this.title = precision.getTitle(referenceDate, getterParams);
        this.items = precision.getItems(referenceDate, getterParams);
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    /**
     * @param {NullableDateTime[]} values
     * @param {number} focusedDateIndex
     */
    adjustFocus(values, focusedDateIndex) {
        if (
            !this.shouldAdjustFocusDate &&
            this.state.focusDate &&
            focusedDateIndex === this.props.focusedDateIndex
        ) {
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
     * @param {DateItem} item
     */
    getActiveRangeInfo({ range }) {
        const values = [...this.values];
        const result = {
            isActive: isInRange(values, range),
            isStart: false,
            isEnd: false,
        };
        if (this.isRange) {
            // Handle active "start" and "end" dates
            if (result.isActive) {
                const [start, end] = values;
                result.isStart = !start || isInRange(start, range);
                result.isEnd = !end || isInRange(end, range);
            }

            // Handle preview state
            if (this.state.hoveredDate) {
                values[this.props.focusedDateIndex] = this.state.hoveredDate;
                // TODO: comment this
                if (values[0] && values[1] && values[1].ts < values[0].ts) {
                    values.reverse();
                }
                const [selectStart, selectEnd] = values;
                if (isInRange(values, range)) {
                    result.isActive = true;
                }
                if (!selectStart || isInRange(selectStart, range)) {
                    result.isStart = true;
                }
                if (!selectEnd || isInRange(selectEnd, range)) {
                    result.isEnd = true;
                }
            }
        } else {
            result.isStart = result.isEnd = result.isActive;
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
                timeValues.push(MERIDIEMS[Math.floor(timeValues[0] / 12) || 0]);
            }
        }
        this.is12HourFormat = !is24HourFormat();
        if (this.is12HourFormat) {
            this.availableHours = [[0, HOURS[12][1]], ...HOURS.slice(1, 12)];
            for (const timeValues of this.state.timeValues) {
                timeValues[0] %= 12;
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
     * Softly moves the selected date by the given duration.
     * @param {import("luxon").DurationLike} duration
     */
    navigate(duration) {
        const { focusedDateIndex } = this.props;
        const value = (this.values[focusedDateIndex] || today()).plus(duration);

        this.shouldAdjustFocusDate = this.validateAndSelect(value, focusedDateIndex);
    }

    /**
     * Goes to the next panel (e.g. next month if precision is "days").
     * If an event is given it will be prevented.
     * @param {Event} [ev]
     */
    next(ev) {
        ev?.preventDefault();
        const { step } = this.activePrecisionLevel;
        this.state.focusDate = this.clamp(this.state.focusDate.plus(step));
    }

    /**
     * Goes to the previous panel (e.g. previous month if precision is "days").
     * If an event is given it will be prevented.
     * @param {Event} [ev]
     */
    previous(ev) {
        ev?.preventDefault();
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
        const result = [...this.values];
        if (this.isRange) {
            if (value.endOf("day") < result[0]) {
                valueIndex = 0;
            } else if (value.startOf("day") > result[1]) {
                valueIndex = 1;
            }
        }
        if (this.props.type === "datetime") {
            // Adjusts result according to the current time values
            const [hour, minute, second] = this.getTimeValues(valueIndex);
            value = value.set({ hour, minute, second });
        }
        if (!isInRange(value, [this.minDate, this.maxDate])) {
            // Date is outside range defined by min and max dates
            return false;
        }
        result[valueIndex] = value;
        this.props.onSelect(this.isRange ? result : result[0]);
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
        if (dateItem.isInvalid) {
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
        this.shouldAdjustFocusDate = isValid && !this.isRange;
    }

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @param {KeyboardEvent} ev
     */
    onWindowKeyDown(ev) {
        const preventAnd = () => ev.preventDefault();

        switch (ev.key) {
            case "n": {
                return preventAnd(this.next(ev));
            }
            case "p": {
                return preventAnd(this.previous(ev));
            }
        }

        if (this.state.precision === "days" && ev.ctrlKey) {
            switch (ev.key) {
                case "ArrowDown": {
                    return preventAnd(this.navigate({ week: +1 }));
                }
                case "ArrowLeft": {
                    return preventAnd(this.navigate({ day: -1 }));
                }
                case "ArrowRight": {
                    return preventAnd(this.navigate({ day: +1 }));
                }
                case "ArrowUp": {
                    return preventAnd(this.navigate({ week: -1 }));
                }
            }
        }
    }
}
