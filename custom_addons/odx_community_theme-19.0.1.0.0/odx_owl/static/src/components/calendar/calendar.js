/** @odoo-module **/

import { Component, markRaw, onMounted, onWillUpdateProps, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { cn } from "@odx_owl/core/utils/cn";
import {
    addDays,
    addMonths,
    compareDays,
    endOfWeek,
    findNearestEnabledDate,
    formatDateValue,
    getMonthWeeks,
    getWeekdayLabels,
    isDateDisabled,
    isDateInRange,
    isSameDay,
    isSameMonth,
    normalizeDateRange,
    normalizeDateValue,
    resolveWeekStartsOn,
    startOfMonth,
    startOfWeek,
    toISODate,
    toISODateRange,
    today,
} from "@odx_owl/core/utils/dates";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId, sanitizeIdFragment } from "@odx_owl/core/utils/ids";

function resolveCalendarMode(mode) {
    return mode === "range" ? "range" : "single";
}

function normalizeCalendarValue(value, mode) {
    return mode === "range" ? normalizeDateRange(value) : normalizeDateValue(value);
}

function getFocusReferenceDate(value, mode) {
    if (mode === "range") {
        return value?.to || value?.from || null;
    }
    return value || null;
}

function getMonthReferenceDate(value, mode) {
    if (mode === "range") {
        return value?.from || value?.to || null;
    }
    return value || null;
}

function isSameRangeValue(left, right) {
    return (
        isSameDay(left?.from, right?.from) &&
        isSameDay(left?.to, right?.to)
    );
}

function isSameCalendarValue(left, right, mode) {
    return mode === "range" ? isSameRangeValue(left, right) : isSameDay(left, right);
}

function toStateDate(value) {
    const date = normalizeDateValue(value);
    return date ? markRaw(date) : null;
}

function toStateRange(value) {
    const range = normalizeDateRange(value);
    if (!range) {
        return null;
    }
    return markRaw({
        from: toStateDate(range.from),
        to: toStateDate(range.to),
    });
}

function toStateCalendarValue(value, mode) {
    return mode === "range" ? toStateRange(value) : toStateDate(value);
}

export class Calendar extends Component {
    static template = "odx_owl.Calendar";
    static props = {
        ariaLabel: { type: String, optional: true },
        autoFocus: { type: Boolean, optional: true },
        className: { type: String, optional: true },
        defaultMonth: { optional: true, validate: () => true },
        defaultValue: { optional: true, validate: () => true },
        disabled: { type: Boolean, optional: true },
        disabledDates: { optional: true, validate: () => true },
        dir: { type: String, optional: true },
        fixedWeeks: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        locale: { type: String, optional: true },
        maxDate: { optional: true, validate: () => true },
        minDate: { optional: true, validate: () => true },
        mode: { type: String, optional: true },
        name: { type: String, optional: true },
        numberOfMonths: { type: Number, optional: true },
        onMonthChange: { type: Function, optional: true },
        onValueChange: { type: Function, optional: true },
        pagedNavigation: { type: Boolean, optional: true },
        showOutsideDays: { type: Boolean, optional: true },
        value: { optional: true, validate: () => true },
        weekStartsOn: { type: Number, optional: true },
    };
    static defaultProps = {
        autoFocus: false,
        className: "",
        disabled: false,
        fixedWeeks: true,
        mode: "single",
        numberOfMonths: 1,
        pagedNavigation: false,
        showOutsideDays: true,
    };

    setup() {
        const mode = this.mode;
        const normalizedValue = normalizeCalendarValue(this.props.value ?? this.props.defaultValue, mode);
        const initialReferenceDate =
            normalizeDateValue(this.props.defaultMonth) ||
            getMonthReferenceDate(normalizedValue, mode) ||
            today();
        const initialMonth = toStateDate(startOfMonth(initialReferenceDate));

        this.state = useState({
            baseId: nextId("odx-calendar"),
            focusedDate: toStateDate(
                getFocusReferenceDate(normalizedValue, mode) || this.resolveInitialFocus(initialMonth)
            ),
            month: initialMonth,
            value: toStateCalendarValue(normalizedValue, mode),
        });
        this.handleNavigateMonth = (offset) => this.navigateMonth(offset);
        this.handleDayFocus = (value) => this.onDayFocus(value);
        this.handleDayKeydown = (value, ev) => this.onDayKeydown(value, ev);
        this.handleSelectDate = (value) => this.selectDate(value);

        onMounted(() => {
            if (this.props.autoFocus) {
                this.focusDate(this.activeDate);
            }
        });

        onWillUpdateProps((nextProps) => {
            const nextMode = resolveCalendarMode(nextProps.mode ?? this.props.mode);
            const nextValue =
                nextProps.value !== undefined
                    ? normalizeCalendarValue(nextProps.value, nextMode)
                    : undefined;
            const currentValue = normalizeCalendarValue(this.props.value, nextMode);
            if (
                nextValue !== undefined &&
                !isSameCalendarValue(nextValue, currentValue, nextMode)
            ) {
                const monthReferenceDate = getMonthReferenceDate(nextValue, nextMode);
                const focusReferenceDate = getFocusReferenceDate(nextValue, nextMode);
                this.state.value = toStateCalendarValue(nextValue, nextMode);
                if (monthReferenceDate) {
                    this.state.month = toStateDate(startOfMonth(monthReferenceDate));
                }
                if (focusReferenceDate) {
                    this.state.focusedDate = toStateDate(focusReferenceDate);
                }
            }
            const nextDefaultMonth = startOfMonth(nextProps.defaultMonth);
            const currentDefaultMonth = startOfMonth(this.props.defaultMonth);
            if (
                nextProps.value === undefined &&
                nextProps.defaultMonth !== undefined &&
                !isSameDay(nextDefaultMonth, currentDefaultMonth)
            ) {
                const nextMonth = nextDefaultMonth;
                if (nextMonth) {
                    this.state.month = toStateDate(nextMonth);
                    this.state.focusedDate = toStateDate(
                        findNearestEnabledDate(nextMonth, this.dateOptions, 1) || nextMonth
                    );
                }
            }
        });
    }

    get activeDate() {
        return (
            this.state.focusedDate ||
            getFocusReferenceDate(this.currentValue, this.mode) ||
            this.resolveInitialFocus(this.visibleMonth) ||
            today()
        );
    }

    get calendarId() {
        return this.props.id || this.state.baseId;
    }

    get classes() {
        return cn("odx-calendar", this.props.className);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get isRtl() {
        return isRtlDirection(this.direction);
    }

    get currentValue() {
        return normalizeCalendarValue(this.props.value ?? this.state.value, this.mode);
    }

    get dateOptions() {
        return {
            disabledDates: this.props.disabledDates,
            maxDate: this.props.maxDate,
            minDate: this.props.minDate,
        };
    }

    get mode() {
        return resolveCalendarMode(this.props.mode);
    }

    get numberOfMonths() {
        return Math.max(1, Number(this.props.numberOfMonths) || 1);
    }

    get navigationStep() {
        return this.props.pagedNavigation ? this.numberOfMonths : 1;
    }

    get minimumMonth() {
        return startOfMonth(this.props.minDate);
    }

    get maximumMonth() {
        return startOfMonth(this.props.maxDate);
    }

    get selectedDate() {
        return this.mode === "single" ? this.currentValue : null;
    }

    get selectedIsoRange() {
        return toISODateRange(this.selectedRange);
    }

    get selectedIsoValue() {
        return toISODate(this.selectedDate);
    }

    get selectedRange() {
        return this.mode === "range" ? this.currentValue : null;
    }

    get visibleMonth() {
        return startOfMonth(
            this.state.month || getMonthReferenceDate(this.currentValue, this.mode) || today()
        );
    }

    get visibleMonths() {
        return Array.from({ length: this.numberOfMonths }, (_, index) => addMonths(this.visibleMonth, index));
    }

    get weekStartsOn() {
        return resolveWeekStartsOn(this.props.weekStartsOn, this.props.locale);
    }

    get weekdayLabels() {
        return getWeekdayLabels(this.weekStartsOn, this.props.locale, "short");
    }

    computeNextRange(selectedDate) {
        const currentRange = this.selectedRange;
        if (!currentRange?.from || currentRange.to) {
            return { from: selectedDate, to: null };
        }
        if (compareDays(selectedDate, currentRange.from) < 0) {
            return { from: selectedDate, to: currentRange.from };
        }
        return { from: currentRange.from, to: selectedDate };
    }

    focusDate(value) {
        const targetId = this.getDayId(value);
        browser.requestAnimationFrame(() => document.getElementById(targetId)?.focus());
    }

    getCaptionId(index) {
        return `${this.calendarId}-caption-${index}`;
    }

    getDayClasses(day) {
        return cn("odx-calendar__day", {
            "odx-calendar__day--disabled": this.isDisabled(day.date),
            "odx-calendar__day--focused": isSameDay(day.date, this.activeDate),
            "odx-calendar__day--hidden": this.isHidden(day),
            "odx-calendar__day--outside": day.isOutside,
            "odx-calendar__day--range-end": this.isRangeEnd(day.date),
            "odx-calendar__day--range-middle": this.isRangeMiddle(day.date),
            "odx-calendar__day--range-start": this.isRangeStart(day.date),
            "odx-calendar__day--selected": this.isSelected(day.date),
            "odx-calendar__day--today": this.isToday(day.date),
        });
    }

    getDayId(value) {
        return `${this.calendarId}-day-${sanitizeIdFragment(toISODate(value))}`;
    }

    getDayKey(day) {
        return toISODate(day.date);
    }

    getDayLabel(value) {
        return formatDateValue(value, { dateStyle: "full" }, this.props.locale);
    }

    getDayNumber(day) {
        return day.date.getDate();
    }

    getDayTabIndex(day) {
        return !this.isHidden(day) && !this.isDisabled(day.date) && isSameDay(day.date, this.activeDate)
            ? 0
            : -1;
    }

    getHiddenInputName(part) {
        return this.mode === "range" ? `${this.props.name}[${part}]` : this.props.name;
    }

    getMonthKey(month) {
        return toISODate(month);
    }

    getMonthLabel(month) {
        return formatDateValue(month, { month: "long", year: "numeric" }, this.props.locale);
    }

    get previousNavPath() {
        return this.isRtl
            ? "M6.25 3.5L10.75 8L6.25 12.5"
            : "M9.75 3.5L5.25 8L9.75 12.5";
    }

    get nextNavPath() {
        return this.isRtl
            ? "M9.75 3.5L5.25 8L9.75 12.5"
            : "M6.25 3.5L10.75 8L6.25 12.5";
    }

    getWeekKey(week) {
        return week.map((day) => toISODate(day.date)).join("-");
    }

    getWeeksForMonth(month) {
        return getMonthWeeks(month, {
            fixedWeeks: this.props.fixedWeeks,
            showOutsideDays: this.props.showOutsideDays,
            weekStartsOn: this.weekStartsOn,
        });
    }

    isDisabled(value) {
        return this.props.disabled || isDateDisabled(value, this.dateOptions);
    }

    isHidden(day) {
        return day.isOutside && !this.props.showOutsideDays;
    }

    isRangeEnd(value) {
        return Boolean(this.selectedRange?.to && isSameDay(value, this.selectedRange.to));
    }

    isRangeMiddle(value) {
        return Boolean(
            this.selectedRange?.from &&
            this.selectedRange?.to &&
            isDateInRange(value, this.selectedRange) &&
            !this.isRangeStart(value) &&
            !this.isRangeEnd(value)
        );
    }

    isRangeStart(value) {
        return Boolean(this.selectedRange?.from && isSameDay(value, this.selectedRange.from));
    }

    isSelected(value) {
        if (this.mode === "range") {
            return isDateInRange(value, this.selectedRange);
        }
        return isSameDay(value, this.selectedDate);
    }

    isToday(value) {
        return isSameDay(value, today());
    }

    moveFocus(value, direction = 1) {
        const normalized = normalizeDateValue(value);
        if (!normalized) {
            return;
        }
        const targetDate = findNearestEnabledDate(normalized, this.dateOptions, direction) || normalized;
        this.state.focusedDate = toStateDate(targetDate);
        if (!isSameMonth(targetDate, this.visibleMonth)) {
            this.state.month = toStateDate(startOfMonth(targetDate));
            this.props.onMonthChange?.(this.state.month);
        }
        this.focusDate(targetDate);
    }

    navigateMonth(offset) {
        const step = Number(offset || 0) * this.navigationStep;
        if (step < 0 && !this.canNavigatePrevious()) {
            return;
        }
        if (step > 0 && !this.canNavigateNext()) {
            return;
        }
        const nextMonth = addMonths(this.visibleMonth, step);
        if (!nextMonth) {
            return;
        }
        this.state.month = toStateDate(startOfMonth(nextMonth));
        this.props.onMonthChange?.(this.state.month);

        const referenceDate = getFocusReferenceDate(this.currentValue, this.mode) || nextMonth;
        this.state.focusedDate = toStateDate(
            findNearestEnabledDate(referenceDate, this.dateOptions, step >= 0 ? 1 : -1) ||
                referenceDate
        );
        this.focusDate(this.state.focusedDate);
    }

    onDayFocus(value) {
        const normalized = normalizeDateValue(value);
        if (normalized) {
            this.state.focusedDate = toStateDate(normalized);
        }
    }

    onDayKeydown(value, ev) {
        if (
            ![
                "ArrowDown",
                "ArrowLeft",
                "ArrowRight",
                "ArrowUp",
                "End",
                "Enter",
                "Home",
                " ",
                "PageDown",
                "PageUp",
            ].includes(ev.key)
        ) {
            return;
        }
        ev.preventDefault();

        const current = normalizeDateValue(value) || this.activeDate;
        if (ev.key === " " || ev.key === "Enter") {
            this.selectDate(current);
            return;
        }

        if (ev.key === "Home") {
            this.moveFocus(startOfWeek(current, this.weekStartsOn), 1);
            return;
        }
        if (ev.key === "End") {
            this.moveFocus(endOfWeek(current, this.weekStartsOn), -1);
            return;
        }
        if (ev.key === "PageUp") {
            this.moveFocus(addMonths(current, ev.shiftKey ? -12 : -1), -1);
            return;
        }
        if (ev.key === "PageDown") {
            this.moveFocus(addMonths(current, ev.shiftKey ? 12 : 1), 1);
            return;
        }

        const deltaMap = {
            ArrowDown: 7,
            ArrowLeft: this.isRtl ? 1 : -1,
            ArrowRight: this.isRtl ? -1 : 1,
            ArrowUp: -7,
        };
        this.moveFocus(addDays(current, deltaMap[ev.key]), deltaMap[ev.key]);
    }

    resolveInitialFocus(month) {
        return (
            findNearestEnabledDate(month, this.dateOptions, 1) ||
            findNearestEnabledDate(today(), this.dateOptions, 1) ||
            today()
        );
    }

    selectDate(value) {
        const selectedDate = normalizeDateValue(value);
        if (!selectedDate || this.isDisabled(selectedDate)) {
            return;
        }

        if (this.mode === "range") {
            const nextRange = this.computeNextRange(selectedDate);
            if (this.props.value === undefined) {
                this.state.value = toStateCalendarValue(nextRange, this.mode);
            }
            this.state.focusedDate = toStateDate(selectedDate);
            this.props.onValueChange?.(nextRange, toISODateRange(nextRange));
            return;
        }

        if (this.props.value === undefined) {
            this.state.value = toStateCalendarValue(selectedDate, this.mode);
        }
        this.state.focusedDate = toStateDate(selectedDate);
        this.props.onValueChange?.(selectedDate, toISODate(selectedDate));
    }

    showNextNav(index) {
        return index === this.visibleMonths.length - 1;
    }

    showPreviousNav(index) {
        return index === 0;
    }

    canNavigatePrevious() {
        if (this.props.disabled) {
            return false;
        }
        if (!this.minimumMonth) {
            return true;
        }
        const previousMonth = startOfMonth(addMonths(this.visibleMonth, -this.navigationStep));
        return Boolean(previousMonth && compareDays(previousMonth, this.minimumMonth) >= 0);
    }

    canNavigateNext() {
        if (this.props.disabled) {
            return false;
        }
        if (!this.maximumMonth) {
            return true;
        }
        const nextMonth = startOfMonth(addMonths(this.visibleMonth, this.navigationStep));
        const lastVisibleMonth = startOfMonth(addMonths(nextMonth, this.numberOfMonths - 1));
        return Boolean(lastVisibleMonth && compareDays(lastVisibleMonth, this.maximumMonth) <= 0);
    }
}
