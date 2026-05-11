import { onWillRender, useRef, useState } from "@web/owl2/utils";
import { Component, onWillUpdateProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { MAX_VALID_DATE, MIN_VALID_DATE, clampDate, isInRange, today } from "../l10n/dates";
import { localization } from "../l10n/localization";
import { ensureArray } from "../utils/arrays";
import { TimePicker } from "@web/core/time_picker/time_picker";
import { Time } from "@web/core/l10n/time";
import { range } from "@web/core/utils/numbers";
import { useNavigation } from "../navigation/navigation";

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
 * @typedef {luxon["DateTime"]["prototype"]} DateTime
 *
 * @typedef DateTimePickerProps
 * @property {number} [focusedDateIndex=0]
 * @property {boolean} [showWeekNumbers=true]
 * @property {DaysOfWeekFormat} [daysOfWeekFormat="narrow"]
 * @property {DateLimit} [maxDate]
 * @property {PrecisionLevel} [maxPrecision="decades"]
 * @property {DateLimit} [minDate]
 * @property {PrecisionLevel} [minPrecision="days"]
 * @property {() => any} [onReset]
 * @property {(value: DateTime | DateRange, unit: "date" | "time") => any} [onSelect]
 * @property {() => any} [onToggleRange]
 * @property {boolean} [range]
 * @property {number} [rounding=5] the rounding in minutes, pass 0 to show seconds, pass 1 to avoid
 *  rounding minutes without displaying seconds.
 * @property {() => boolean} [showRangeToggler]
 * @property {{ buttons?: any }} [slots]
 * @property {"date" | "datetime"} [type]
 * @property {NullableDateTime | NullableDateRange} [value]
 * @property {(date: DateTime) => boolean} [isDateValid]
 * @property {(date: DateTime) => string} [dayCellClass]
 * @property {boolean} [focusTrap=false]
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
        getTitle: (date) => `${date.monthShort} ${date.year}`,
        getItems: (date, { maxDate, minDate, showWeekNumbers, isDateValid, dayCellClass }) => {
            const startDates = [date];

            /** @type {WeekItem[]} */
            const lastWeeks = [];
            let shouldAddLastWeek = false;

            const dayItems = startDates.map((date, i) => {
                const monthRange = [date.startOf("month"), date.endOf("month")];
                /** @type {WeekItem[]} */
                const weeks = [];

                // Generate 6 weeks for current month
                let startOfNextWeek = getStartOfWeek(monthRange[0]);
                for (let w = 0; w < WEEKS_PER_MONTH; w++) {
                    const weekDayItems = [];
                    // Generate all days of the week
                    for (let d = 0; d < DAYS_PER_WEEK; d++) {
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
                        if (d === DAYS_PER_WEEK - 1) {
                            startOfNextWeek = day.plus({ day: 1 });
                        }
                        if (w === WEEKS_PER_MONTH - 1) {
                            shouldAddLastWeek = true;
                        }
                    }

                    const weekItem = toWeekItem(weekDayItems);
                    if (w === WEEKS_PER_MONTH - 1) {
                        lastWeeks.push(weekItem);
                    } else {
                        weeks.push(weekItem);
                    }
                }

                // Generate days of week labels
                const daysOfWeek = weeks[0].days.map((d) => [
                    d.range[0].weekdayShort,
                    d.range[0].weekdayLong,
                    Info.weekdays("narrow", { locale: d.range[0].locale })[d.range[0].weekday - 1],
                ]);
                if (showWeekNumbers) {
                    daysOfWeek.unshift(["", _t("Week numbers"), ""]);
                }

                return {
                    id: `__month__${i}`,
                    number: monthRange[0].month,
                    daysOfWeek,
                    weeks,
                };
            });

            if (shouldAddLastWeek) {
                // Add last empty week item if the other month has an extra week
                for (let i = 0; i < dayItems.length; i++) {
                    dayItems[i].weeks.push(lastWeeks[i]);
                }
            }

            return dayItems;
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
            return range(12).map((month) => {
                const startOfMonth = startOfYear.plus({ month });
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
            return range(-GRID_MARGIN, GRID_COUNT + GRID_MARGIN).map((i) => {
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
            return range(-GRID_MARGIN, GRID_COUNT + GRID_MARGIN).map((i) => {
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

const DAYS_PER_WEEK = 7;
const WEEKS_PER_MONTH = 6;

/** @extends {Component<DateTimePickerProps>} */
export class DateTimePicker extends Component {
    static props = {
        focusedDateIndex: { type: Number, optional: true },
        focusTrap: { type: Boolean, optional: true },
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
        onReset: { type: Function, optional: true },
        onSelect: { type: Function, optional: true },
        onToggleRange: { type: Function, optional: true },
        range: { type: Boolean, optional: true },
        rounding: { type: Number, optional: true },
        showRangeToggler: { type: Boolean, optional: true },
        slots: {
            type: Object,
            shape: { buttons: { type: Object, optional: true } },
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
        focusTrap: false,
        daysOfWeekFormat: "narrow",
        maxPrecision: "decades",
        minPrecision: "days",
        rounding: 5,
        showWeekNumbers: true,
        type: "datetime",
    };

    static template = "web.DateTimePicker";
    static components = { TimePicker };

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

    get _precisionItemsParams() {
        return {
            maxDate: this.maxDate,
            minDate: this.minDate,
            showWeekNumbers: this.props.showWeekNumbers,
            isDateValid: this.props.isDateValid,
            dayCellClass: this.props.dayCellClass,
        };
    }

    //-------------------------------------------------------------------------
    // Lifecycle
    //-------------------------------------------------------------------------

    setup() {
        /** @type {PrecisionLevel[]} */
        this.allowedPrecisionLevels = [];
        /** @type {Item[]} */
        this.items = [];
        this.title = "";
        this.shouldAdjustFocusDate = false;
        this.shouldFocusDateCell = false;
        // Allow the zoomOrSelect method to detect if the action was triggered
        // by navigation or by a real user interaction (isTrusted)
        this.actionTriggeredByNavigation = false;
        this.rootRef = useRef("root");
        this.timePickerContainerRef = useRef("timePickerContainer");

        this.state = useState({
            /** @type {DateTime | null} */
            activeDate: null,
            /** @type {DateTime | null} */
            focusDate: null,
            /** @type {DateTime | null} */
            hoveredDate: null,
            /** @type {DateTime | null} */
            navigationDate: null,
            /** @type {Time[]} */
            timeValues: [],
            /** @type {PrecisionLevel} */
            precision: this.props.minPrecision,
        });

        this.onPropsUpdated(this.props);
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));

        onWillRender(() => this.onWillRender());

        this._setupNavigation();
    }

    /**
     * @param {DateTimePickerProps} props
     */
    onPropsUpdated(props) {
        /** @type {[NullableDateTime] | NullableDateRange} */
        this.values = ensureArray(props.value).map((value) =>
            value && !value.isValid ? null : value
        );
        this.allowedPrecisionLevels = this.filterPrecisionLevels(
            props.minPrecision,
            props.maxPrecision
        );

        this.maxDate = parseLimitDate(props.maxDate, MAX_VALID_DATE);
        this.minDate = parseLimitDate(props.minDate, MIN_VALID_DATE);
        if (this.props.type === "date") {
            this.maxDate = this.maxDate.endOf("day");
            this.minDate = this.minDate.startOf("day");
        }

        if (this.maxDate < this.minDate) {
            throw new Error(`DateTimePicker error: given "maxDate" comes before "minDate".`);
        }

        this.state.timeValues = this.getTimeValues(props);
        this.shouldAdjustFocusDate = !props.range;
        this.setNavigationDate(
            this.values[props.focusedDateIndex] ||
                this.values[props.focusedDateIndex === 1 ? 0 : 1] ||
                this._getNextValidDate(today(), "days", 1)
        );
        this.adjustFocus(this.state.navigationDate);
    }

    onWillRender() {
        const { focusedDateIndex, range } = this.props;
        const { focusDate, activeDate } = this.state;
        const precision = this.activePrecisionLevel;

        this.title = precision.getTitle(focusDate);
        this.items = precision.getItems(focusDate, this._precisionItemsParams);

        this.selectedRange = [...this.values];
        if (range && focusedDateIndex > 0 && (!this.values[1] || activeDate > this.values[0])) {
            this.selectedRange[1] = activeDate;
        }
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    /**
     * @private
     */
    _adjustNavigationDate() {
        const range = [this.state.focusDate, this.state.focusDate.endOf("month")];
        let date = this.state.navigationDate || this.state.focusDate;

        if (isInRange(this.values?.[this.props.focusedDateIndex], range)) {
            date = this.values[this.props.focusedDateIndex];
        } else if (this.state.precision === "days") {
            if (!isInRange(date, range)) {
                date = this.state.focusDate;
            }
            date = this._getNextValidDate(date, this.state.precision, 1);
        } else {
            const items = this.activePrecisionLevel.getItems(this.state.focusDate, this._precisionItemsParams);

            date = items.find((item) => isInRange(date, item.range))?.range[0] ?? this.state.focusDate;
        }

        this.setNavigationDate(date);
    }

    /**
     * @private
     */
    _getNextValidDate(activeDate, unit, delta) {
        if (this.state.precision !== "days") {
            return activeDate;
        }

        while (
            isInRange(activeDate, [this.minDate, this.maxDate]) &&
            this.props.isDateValid &&
            !this.props.isDateValid(activeDate)
        ) {
            activeDate = activeDate.plus({ [unit]: delta });
        }

        return activeDate;
    }

    /**
     * @private
     */
    _setupNavigation() {
        const focusDateCell = (navigator) => {
            let date = this.state.navigationDate;

            if (date) {
                // Since the navigator uses the dataset itemId (record.id) of the record,
                // we have to adapt the date to match the itemId
                if (this.state.precision === "days") {
                    date = date.startOf("day");
                } else {
                    date = date.startOf("month");
                }
                date = date.toISODate();
                navigator.items.find((item) => item.el.dataset.itemId === date)?.setActive();
            }
        };

        const onArrowKeyCallback = (navigator, key) => {
            let date = this.state.navigationDate;
            let unit = this.state.precision;
            let offset, delta, minDate, maxDate;

            if (this.state.precision === "days") {
                delta = 7;
                minDate = this.state.focusDate.startOf("month");
                maxDate = this.state.focusDate.endOf("month");
            } else {
                delta = 4;
                minDate = this.items[0].range[0];
                maxDate = this.items[this.items.length - 1].range[1];
            }

            switch (key) {
                case "arrowright":
                    offset = 1;
                    break;
                case "arrowleft":
                    offset = -1;
                    break;
                case "arrowup":
                    offset = -delta;
                    break;
                case "arrowdown":
                    offset = delta;
                    break;
            }

            if (this.state.precision === "decades") {
                unit = "year";
                offset = offset *= 10;
            }

            date = this._getNextValidDate(this.clamp(date.plus({ [unit]: offset })), unit, offset < 0 ? -1 : 1);

            // If out of range, skip the navigation
            if (!isInRange(date, [this.minDate, this.maxDate])) {
                return;
            }

            this.setNavigationDate(date);

            // Active date moved outside the visible panel, shift the focusDate to follow.
            if (!isInRange(this.state.activeDate, [minDate, maxDate])) {
                this.state.focusDate = this.clamp(this.state.activeDate.startOf("month"));
                this.shouldFocusDateCell = true;
            } else {
                focusDateCell(navigator);
            }
        };

        const arrowsNavigationOptions = {};

        for (const key of ["arrowup", "arrowright", "arrowdown", "arrowleft"]) {
            arrowsNavigationOptions[key] = {
                isAvailable: ({ navigator }) =>
                    Boolean(navigator.activeItem) && navigator.activeItem.el.classList.contains("o_date_item_cell"),
                callback: (navigator) => onArrowKeyCallback(navigator, key),
                bypassEditableProtection: true,
            };
        }

        const getNavigableItems = (navigator) =>
            navigator.items.filter((item) => item.el.classList.contains("o-navigable"));

        const tabKeyCallback = (navigator, offset) => {
            const items = getNavigableItems(navigator);
            const activeItemIndex = items.indexOf(navigator.activeItem);

            let nextIndex = activeItemIndex + offset;

            if (nextIndex < 0) {
                nextIndex = items.length - 1;
            } else if (nextIndex >= items.length) {
                nextIndex = 0;
            }

            items[nextIndex]?.setActive();
        };

        const actionKeyCallback = (navigator) => {
            this.actionTriggeredByNavigation = true;
            navigator.activeItem.select();
        };

        const forceCloseCallback = (date) => {
            if (!date) {
                this.props.onReset?.();
            } else {
                this.validateAndSelect(date, this.props.focusedDateIndex, "date", true);
            }
        };

        useNavigation(this.rootRef, {
            getItems: () => this.rootRef.el?.querySelectorAll(".o-navigable, .o_date_item_cell") ?? [],
            isNavigationAvailable: ({ target }) => this.rootRef.el?.contains(target) || this.props.focusTrap,
            onUpdated: (navigator) => {
                if (this.shouldFocusDateCell) {
                    this.shouldFocusDateCell = false;
                    focusDateCell(navigator);
                }
            },
            hotkeys: {
                tab: {
                    isAvailable: ({ navigator }) => {
                        if (this.props.focusTrap) {
                            return true;
                        }
                        const items = getNavigableItems(navigator);
                        return items.indexOf(navigator.activeItem) < items.length - 1;
                    },
                    callback: (navigator) => tabKeyCallback(navigator, 1),
                    bypassEditableProtection: true,
                },
                "shift+tab": {
                    isAvailable: ({ navigator }) => {
                        if (this.props.focusTrap) {
                            return true;
                        }
                        const items = getNavigableItems(navigator);
                        return items.indexOf(navigator.activeItem) > 0;
                    },
                    callback: (navigator) => tabKeyCallback(navigator, -1),
                    bypassEditableProtection: true,
                },
                "control+enter": {
                    isAvailable: ({ navigator }) => Boolean(navigator.activeItem),
                    callback: () => forceCloseCallback(this.state.navigationDate),
                    bypassEditableProtection: true,
                },
                enter: {
                    isAvailable: ({ navigator, target }) =>
                        Boolean(navigator.activeItem) && !this.timePickerContainerRef?.el.contains(target),
                    callback: actionKeyCallback,
                    bypassEditableProtection: true,
                },
                space: {
                    isAvailable: ({ navigator, target }) =>
                        Boolean(navigator.activeItem) && !this.timePickerContainerRef?.el.contains(target),
                    callback: actionKeyCallback,
                    bypassEditableProtection: true,
                },
                escape: {
                    isAvailable: ({ navigator }) => Boolean(navigator.activeItem),
                    callback: () => forceCloseCallback(this.values[this.props.focusedDateIndex]),
                    bypassEditableProtection: true,
                },
                ...arrowsNavigationOptions,
            },
        });
    }

    /**
     * @param {DateTime} dateToFocus
     */
    adjustFocus(dateToFocus) {
        if (!this.shouldAdjustFocusDate && this.state.focusDate) {
            return;
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
     * Returns various flags indicating what ranges the current date item belongs
     * to. Note that these ranges are computed differently according to the current
     * value mode (range or single date). This is done to simplify CSS selectors.
     * - Selected Range:
     *      > range: current values with active date applied
     *      > single date: just the active date
     * - Highlighted Range:
     *      > range: union of selection range and current values
     *      > single date: just the current value
     * - Current Range (range only):
     *      > range: current start date or current end date.
     * @param {DateItem} item
     */
    getActiveRangeInfo({ range }) {
        const result = {
            isSelected: isInRange(this.selectedRange, range),
            isSelectStart: false,
            isSelectEnd: false,
            isHighlighted: isInRange(this.state.activeDate, range),
            isNavigable: isInRange(this.state.navigationDate, range),
        };

        if (this.props.range) {
            if (result.isSelected) {
                const [selectStart, selectEnd] = this.selectedRange.sort();
                result.isSelectStart = !selectStart || isInRange(selectStart, range);
                result.isSelectEnd = !selectEnd || isInRange(selectEnd, range);
            }
        } else {
            result.isSelectStart = result.isSelectEnd = result.isSelected;
        }

        return result;
    }

    /**
     * @param {DateTimePickerProps} props
     */
    getTimeValues(props) {
        const timeValues = this.values.map(
            (val, index) =>
                new Time({
                    hour:
                        index === 1 && !this.values[1]
                            ? (val || DateTime.local()).hour + 1
                            : (val || DateTime.local()).hour,
                    minute: val?.minute || 0,
                    second: val?.second || 0,
                })
        );

        if (props.range) {
            return timeValues;
        } else {
            const values = [];
            values[props.focusedDateIndex] = timeValues[props.focusedDateIndex];
            return values;
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
        this.state.focusDate = this.clamp(this.state.focusDate.plus(step).startOf("month"));
        this._adjustNavigationDate();
    }

    /**
     * Goes to the previous panel (e.g. previous month if precision is "days").
     * If an event is given it will be prevented.
     * @param {PointerEvent} ev
     */
    previous(ev) {
        ev.preventDefault();
        const { step } = this.activePrecisionLevel;
        this.state.focusDate = this.clamp(this.state.focusDate.minus(step).startOf("month"));
        this._adjustNavigationDate();
    }

    /**
     * @param {number} valueIndex
     * @param {Time} newTime
     */
    onTimeChange(valueIndex, newTime) {
        this.state.timeValues[valueIndex] = newTime;
        const value = this.values[valueIndex] || today();
        this.validateAndSelect(value, valueIndex, "time");
    }

    /**
     * @param {DateTime} date
     */
    setHoveredDate(date) {
        this.state.hoveredDate = date ? this.clamp(date) : null;

        if (date) {
            this.state.activeDate = this.state.hoveredDate;
        }
    }

    /**
     * @param {DateTime} date
     */
    setNavigationDate(date) {
        this.state.navigationDate = date ? this.clamp(date) : null;

        if (date) {
            this.state.activeDate = this.state.navigationDate;
        }
    }

    /**
     * @param {DateTime} value
     * @param {number} valueIndex
     * @param {"date" | "time"} unit
     * @param {boolean} shouldApply
     */
    validateAndSelect(value, valueIndex, unit, shouldApply = false) {
        if (!this.props.onSelect) {
            // No onSelect handler
            return false;
        }

        const result = [...this.values];
        result[valueIndex] = value;

        if (this.props.type === "datetime") {
            // Adjusts result according to the current time values
            const { hour, minute, second } = this.state.timeValues[valueIndex];
            result[valueIndex] = result[valueIndex].set({ hour, minute, second });
        }
        if (!isInRange(result[valueIndex], [this.minDate, this.maxDate])) {
            // Date is outside range defined by min and max dates
            return false;
        }
        this.props.onSelect(result.length === 2 ? result : result[0], unit, shouldApply);
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
            this._adjustNavigationDate();
            this.shouldFocusDateCell = true;
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
            this._adjustNavigationDate();
            return true;
        }
        return false;
    }

    /**
     * Happens when a date item is selected:
     * - first tries to zoom in on the item
     * - if could not zoom in: date is considered as final value and triggers a hard select
     * @param {Event} event
     * @param {DateItem} dateItem
     */
    zoomOrSelect(event, dateItem) {
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
        const shouldApply =
            (!this.actionTriggeredByNavigation || event.isTrusted) && !this.props.range && this.props.type === "date";
        const isValid = this.validateAndSelect(value, valueIndex, "date", shouldApply);
        this.shouldAdjustFocusDate = isValid && !this.props.range;

        if (this.actionTriggeredByNavigation || event.isTrusted) {
            this.actionTriggeredByNavigation = false;
        }
    }
}
