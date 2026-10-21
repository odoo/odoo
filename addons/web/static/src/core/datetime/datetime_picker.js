import { Component, computed, onPatched, proxy, t, useOnChange, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { MAX_VALID_DATE, MIN_VALID_DATE, clampDate, isInRange, today } from "../l10n/dates";
import { localization } from "../l10n/localization";
import { ensureArray } from "../utils/arrays";
import { TimePicker } from "@web/core/time_picker/time_picker";
import { Time } from "@web/core/l10n/time";
import { range } from "@web/core/utils/numbers";

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
                /** @type {(TranslatedString | null)[][]} */
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
const SWIPE_THRESHOLD = 50; // px
const SWIPE_LOCK_DISTANCE = 10; // px
const SWIPE_MIN_VELOCITY = 0.3; // px/ms
const SWIPE_ANIMATION_DURATION = 250; // ms
const SWIPE_RESISTANCE = 3; // drag slow down when there is no panel to show

const DAYS_PER_WEEK = 7;
const WEEKS_PER_MONTH = 6;

const NULLABLE_DATETIME_TYPE = t.or([t.instanceOf(DateTime), t.literal(false), t.literal(null)]);

export const dateTimePickerProps = {
    focusedDateIndex: t.number().optional(0),
    showWeekNumbers: t.boolean().optional(true),
    daysOfWeekFormat: t.string().optional("narrow"),
    maxDate: t.or([NULLABLE_DATETIME_TYPE, t.literal("today")]).optional(),
    maxPrecision: t.selection([...PRECISION_LEVELS.keys()]).optional("decades"),
    minDate: t.or([NULLABLE_DATETIME_TYPE, t.literal("today")]).optional(),
    minPrecision: t.selection([...PRECISION_LEVELS.keys()]).optional("days"),
    onReset: t.function().optional(),
    onSelect: t.function().optional(),
    onToggleRange: t.function().optional(),
    range: t.boolean().optional(),
    rounding: t.number().optional(5),
    showRangeToggler: t.boolean().optional(),
    slots: t.object({ buttons: t.object().optional() }).optional(),
    type: t.selection(["date", "datetime"]).optional("datetime"),
    value: t.or([NULLABLE_DATETIME_TYPE, t.array(NULLABLE_DATETIME_TYPE)]).optional(),
    isDateValid: t.function().optional(),
    dayCellClass: t.function().optional(),
    tz: t.string().optional(),
};

/** @extends {Component<DateTimePickerProps>} */
export class DateTimePicker extends Component {
    props = useProps(dateTimePickerProps);

    static template = "web.DateTimePicker";
    static components = { TimePicker };

    values = computed(() =>
        ensureArray(this.props.value).map((value) => (value && !value.isValid ? null : value))
    );
    maxDate = computed(() => {
        let maxDate = parseLimitDate(this.props.maxDate, MAX_VALID_DATE);
        if (this.props.type === "date") {
            maxDate = maxDate.endOf("day");
        }
        return maxDate;
    });
    minDate = computed(() => {
        let minDate = parseLimitDate(this.props.minDate, MIN_VALID_DATE);
        if (this.props.type === "date") {
            minDate = minDate.startOf("day");
        }
        return minDate;
    });
    title = computed(() => this.activePrecisionLevel.getTitle(this.state.focusDate));
    dateRange = computed(() => {
        const minDate = this.minDate();
        const maxDate = this.maxDate();
        if (maxDate < minDate) {
            throw new Error(`DateTimePicker error: given "maxDate" comes before "minDate".`);
        }
        return { minDate, maxDate };
    });
    items = computed(() => this.getItems(this.state.focusDate));
    selectedRange = computed(() => {
        const values = this.values();
        const selectedRange = [...values];
        if (
            this.props.range &&
            this.props.focusedDateIndex > 0 &&
            (!values[1] || this.state.hoveredDate > values[0])
        ) {
            selectedRange[1] = this.state.hoveredDate;
        }
        return selectedRange;
    });
    allowedPrecisionLevels = computed(() =>
        this.filterPrecisionLevels(this.props.minPrecision, this.props.maxPrecision)
    );

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    get activePrecisionLevel() {
        return PRECISION_LEVELS.get(this.state.precision);
    }

    get isLastPrecisionLevel() {
        return (
            this.allowedPrecisionLevels().indexOf(this.state.precision) ===
            this.allowedPrecisionLevels().length - 1
        );
    }

    get titles() {
        return ensureArray(this.title());
    }

    //-------------------------------------------------------------------------
    // Lifecycle
    //-------------------------------------------------------------------------

    setup() {
        this.shouldAdjustFocusDate = false;

        this.state = proxy({
            /** @type {DateTime | null} */
            focusDate: null,
            /** @type {DateTime | null} */
            hoveredDate: null,
            /** @type {Time[]} */
            timeValues: [],
            /** @type {PrecisionLevel} */
            precision: this.props.minPrecision,
            isSwiping: false,
        });

        useOnChange(
            () => [
                this.props.focusedDateIndex,
                this.props.maxDate,
                this.props.minDate,
                this.props.range,
                this.props.type,
                this.props.value,
            ],
            () => this.onPropsUpdated()
        );

        onPatched(() => {
            this.onNextPatch?.();
            this.onNextPatch = null;
        });
    }

    onPropsUpdated() {
        const values = this.values();
        this.state.timeValues = this.getTimeValues(values);
        this.shouldAdjustFocusDate = !this.props.range;
        this.adjustFocus(values, this.props.focusedDateIndex);
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    /**
     * @param {NullableDateTime[]} values
     * @param {number} focusedDateIndex
     * @param {DateTime} [minDate]
     * @param {DateTime} [maxDate]
     */
    adjustFocus(values, focusedDateIndex, minDate = this.minDate(), maxDate = this.maxDate()) {
        if (!this.shouldAdjustFocusDate && this.state.focusDate) {
            return;
        }

        const dateToFocus =
            values[focusedDateIndex] || values[focusedDateIndex === 1 ? 0 : 1] || today();

        this.shouldAdjustFocusDate = false;
        this.state.focusDate = this.clamp(dateToFocus.startOf("month"), minDate, maxDate);
    }

    /**
     * @param {DateTime} focusDate
     */
    getItems(focusDate) {
        const { minDate, maxDate } = this.dateRange();
        return this.activePrecisionLevel.getItems(focusDate, {
            maxDate,
            minDate,
            showWeekNumbers: this.props.showWeekNumbers ?? !this.props.range,
            isDateValid: this.props.isDateValid,
            dayCellClass: this.props.dayCellClass,
        });
    }

    /**
     * @param {DateTime} value
     * @param {DateTime} [minDate]
     * @param {DateTime} [maxDate]
     */
    clamp(value, minDate = this.minDate(), maxDate = this.maxDate()) {
        return clampDate(value, minDate, maxDate);
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
    getActiveRangeInfo({ range }) {
        const selectedRange = this.selectedRange();
        const result = {
            isSelected: isInRange(selectedRange, range),
            isSelectStart: false,
            isSelectEnd: false,
            isHighlighted: isInRange(this.state.hoveredDate, range),
        };

        if (this.props.range) {
            if (result.isSelected) {
                const [selectStart, selectEnd] = [...selectedRange].sort();
                result.isSelectStart = !selectStart || isInRange(selectStart, range);
                result.isSelectEnd = !selectEnd || isInRange(selectEnd, range);
            }
        } else {
            result.isSelectStart = result.isSelectEnd = result.isSelected;
        }

        return result;
    }

    /**
     * @param {[NullableDateTime] | NullableDateRange} values
     */
    getTimeValues(values) {
        const timeValues = values.map(
            (val, index) =>
                new Time({
                    hour:
                        index === 1 && !values[1]
                            ? (val || DateTime.local()).hour + 1
                            : (val || DateTime.local()).hour,
                    minute: val?.minute || 0,
                    second: val?.second || 0,
                })
        );

        if (this.props.range) {
            return timeValues;
        } else {
            const values = [];
            values[this.props.focusedDateIndex] = timeValues[this.props.focusedDateIndex];
            return values;
        }
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
     * @param {TouchEvent} ev
     */
    onSwipeStart(ev) {
        this.swipe = null;
        if (ev.touches.length !== 1) {
            return;
        }
        const el = ev.currentTarget;
        // Ends a running slide right away
        el.getAnimations().forEach((animation) => animation.finish());
        const { clientX, clientY } = ev.touches[0];
        this.swipe = {
            el,
            startX: clientX,
            startY: clientY,
            startTime: Date.now(),
            deltaX: 0,
            isHorizontal: null,
        };
    }

    /**
     * Makes the panels follow the finger once the gesture is known to be
     * horizontal. Vertical gestures are left to the browser (scroll).
     * @param {TouchEvent} ev
     */
    onSwipeMove(ev) {
        const swipe = this.swipe;
        if (!swipe) {
            return;
        }
        const { clientX, clientY } = ev.touches[0];
        let deltaX = clientX - swipe.startX;
        const deltaY = clientY - swipe.startY;
        if (swipe.isHorizontal === null) {
            if (Math.max(Math.abs(deltaX), Math.abs(deltaY)) < SWIPE_LOCK_DISTANCE) {
                return;
            }
            swipe.isHorizontal = Math.abs(deltaX) > Math.abs(deltaY);
            if (!swipe.isHorizontal) {
                this.swipe = null;
                return;
            }
        }
        // Renders the neighbor panels
        this.state.isSwiping = true;
        if (!this.getSwipeTarget(deltaX)) {
            // Nothing to show on that side: resist the drag
            deltaX /= SWIPE_RESISTANCE;
        }
        swipe.deltaX = deltaX;
        swipe.el.style.transform = `translate3d(${deltaX}px, 0, 0)`;
    }

    /**
     * Swiping horizontally goes to the next or previous panel, depending on
     * the swipe direction (reversed in RTL). The panels then slide to their
     * final position.
     * @param {TouchEvent} ev
     */
    onSwipeEnd(ev) {
        const swipe = this.swipe;
        if (!swipe) {
            return;
        }
        this.swipe = null;
        const { el, deltaX, startTime } = swipe;
        if (!swipe.isHorizontal) {
            el.style.transform = "";
            return;
        }
        const velocity = Math.abs(deltaX) / (Date.now() - startTime || 1);
        const isSwipe =
            Math.abs(deltaX) >= SWIPE_THRESHOLD ||
            (Math.abs(deltaX) >= SWIPE_LOCK_DISTANCE && velocity >= SWIPE_MIN_VELOCITY);
        const target = isSwipe && this.getSwipeTarget(deltaX);
        if (!target) {
            this.slideSwipeBack(el, deltaX);
            return;
        }
        ev.preventDefault();
        // Distance between two panels, gap included
        const neighbor = el.querySelector(":scope > .o_datetime_picker_neighbor");
        const distance = neighbor ? Math.abs(neighbor.offsetLeft) : el.offsetWidth;
        this.state.focusDate = target;
        // Once rendered, the new panel is moved back where it was dragged so
        // that it can slide into place
        this.onNextPatch = () => this.slideSwipeBack(el, deltaX - Math.sign(deltaX) * distance);
    }

    onSwipeCancel() {
        if (this.swipe) {
            this.swipe.el.style.transform = "";
            this.swipe = null;
        }
        this.state.isSwiping = false;
    }

    /**
     * @param {number} deltaX
     * @returns {DateTime | null} the date to focus when swiping by deltaX
     */
    getSwipeTarget(deltaX) {
        const isRTL = localization.direction === "rtl";
        const { previous, next } = this.getSwipeNeighbors();
        return deltaX < 0 !== isRTL ? next : previous;
    }

    /**
     * @returns {{ previous: DateTime | null, next: DateTime | null }}
     */
    getSwipeNeighbors() {
        const { focusDate } = this.state;
        const { step } = this.activePrecisionLevel;
        const previous = this.clamp(focusDate.minus(step));
        const next = this.clamp(focusDate.plus(step));
        return {
            previous: previous.equals(focusDate) ? null : previous,
            next: next.equals(focusDate) ? null : next,
        };
    }

    /**
     * Panels displayed in the swipe area: the current one and, while swiping,
     * the previous and next ones on each side.
     */
    getSwipePanels() {
        const panels = [{ key: "current", items: this.items() }];
        if (this.state.isSwiping) {
            for (const [key, date] of Object.entries(this.getSwipeNeighbors())) {
                if (date) {
                    panels.push({ key, items: this.getItems(date) });
                }
            }
        }
        return panels;
    }

    /**
     * @param {HTMLElement} el
     * @param {number} fromX
     */
    slideSwipeBack(el, fromX) {
        el.style.transform = "";
        const animation = el.animate(
            [{ transform: `translate3d(${fromX}px, 0, 0)` }, { transform: "none" }],
            { duration: SWIPE_ANIMATION_DURATION, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)" }
        );
        animation.onfinish = () => (this.state.isSwiping = false);
    }

    /**
     * @param {number} valueIndex
     * @param {Time} newTime
     */
    onTimeChange(valueIndex, newTime) {
        this.state.timeValues[valueIndex] = newTime;
        const value = this.values()[valueIndex] || today();
        this.validateAndSelect(value, valueIndex, "time");
    }

    /**
     * @param {DateTime} value
     * @param {number} valueIndex
     * @param {"date" | "time"} unit
     */
    validateAndSelect(value, valueIndex, unit) {
        if (!this.props.onSelect) {
            // No onSelect handler
            return false;
        }

        const result = [...this.values()];
        result[valueIndex] = value;

        if (this.props.type === "datetime") {
            // Adjusts result according to the current time values
            const { hour, minute, second } = this.state.timeValues[valueIndex];
            result[valueIndex] = result[valueIndex].set({ hour, minute, second });
        }
        if (!isInRange(result[valueIndex], [this.minDate(), this.maxDate()])) {
            // Date is outside range defined by min and max dates
            return false;
        }
        this.props.onSelect(result.length === 2 ? result : result[0], unit);
        return true;
    }

    /**
     * Returns whether the zoom has occurred
     * @param {DateTime} date
     */
    zoomIn(date) {
        const index = this.allowedPrecisionLevels().indexOf(this.state.precision) - 1;
        if (index in this.allowedPrecisionLevels()) {
            this.state.focusDate = this.clamp(date);
            this.state.precision = this.allowedPrecisionLevels()[index];
            return true;
        }
        return false;
    }

    /**
     * Returns whether the zoom has occurred
     */
    zoomOut() {
        const index = this.allowedPrecisionLevels().indexOf(this.state.precision) + 1;
        if (index in this.allowedPrecisionLevels()) {
            this.state.precision = this.allowedPrecisionLevels()[index];
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
        const isValid = this.validateAndSelect(value, valueIndex, "date");
        this.shouldAdjustFocusDate = isValid && !this.props.range;
    }
}
