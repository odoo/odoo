// @ts-check

/** @module @web/core/py_js/py_date - Python date, datetime, time, and relativedelta emulation in JavaScript */

import {
    assert,
    fmt2,
    fmt4,
    isLeap,
    tmxxx,
    ValueError,
    ymd2ord,
} from "./py_date_helpers";
import { parseArgs } from "./py_parser";
import { PyTimeDelta } from "./py_timedelta";

// Re-export for backward compatibility
export { PyTimeDelta } from "./py_timedelta";

// ─── Errors ──────────────────────────────────────────────────────────────────

export class NotSupportedError extends Error {}

// ─── PyDate ──────────────────────────────────────────────────────────────────

export class PyDate {
    /** @returns {PyDate} */
    static today() {
        return this.convertDate(new Date());
    }

    /**
     * @param {Date} date
     * @returns {PyDate}
     */
    static convertDate(date) {
        const year = date.getFullYear();
        const month = date.getMonth() + 1;
        const day = date.getDate();
        return new PyDate(year, month, day);
    }

    /**
     * @param {number} year
     * @param {number} month
     * @param {number} day
     */
    constructor(year, month, day) {
        this.year = year;
        this.month = month; // 1-indexed => 1 = january, 2 = february, ...
        this.day = day; // 1-indexed => 1 = first day of month, ...
    }

    /**
     * @param  {...any} args
     * @returns {PyDate}
     */
    static create(...args) {
        const { year, month, day } = parseArgs(args, ["year", "month", "day"]);
        return new PyDate(year, month, day);
    }

    /**
     * @param {PyTimeDelta} timedelta
     * @returns {PyDate}
     */
    add(timedelta) {
        const s = tmxxx(this.year, this.month, this.day + timedelta.days);
        return new PyDate(s.year, s.month, s.day);
    }

    /**
     * @param {any} other
     * @returns {boolean}
     */
    isEqual(other) {
        if (!(other instanceof PyDate)) {
            return false;
        }
        return (
            this.year === other.year &&
            this.month === other.month &&
            this.day === other.day
        );
    }

    /**
     * @param {string} format
     * @returns {string}
     */
    strftime(format) {
        return format.replace(/%([A-Za-z])/g, (m, c) => {
            switch (c) {
                case "Y":
                    return fmt4(this.year);
                case "m":
                    return fmt2(this.month);
                case "d":
                    return fmt2(this.day);
            }
            throw new ValueError(`No known conversion for ${m}`);
        });
    }

    /**
     * @param {PyTimeDelta | PyDate} other
     * @returns {PyDate | PyTimeDelta}
     */
    substract(other) {
        if (other instanceof PyTimeDelta) {
            return this.add(other.negate());
        }
        if (other instanceof PyDate) {
            return PyTimeDelta.create(this.toordinal() - other.toordinal());
        }
        throw new NotSupportedError();
    }

    /** @returns {string} */
    toJSON() {
        return this.strftime("%Y-%m-%d");
    }

    /** @returns {number} */
    toordinal() {
        return ymd2ord(this.year, this.month, this.day);
    }
}

// ─── PyDateTime ──────────────────────────────────────────────────────────────

export class PyDateTime {
    /** @returns {PyDateTime} */
    static now() {
        return this.convertDate(new Date());
    }

    /**
     * @param {Date} date
     * @returns {PyDateTime}
     */
    static convertDate(date) {
        const year = date.getFullYear();
        const month = date.getMonth() + 1;
        const day = date.getDate();
        const hour = date.getHours();
        const minute = date.getMinutes();
        const second = date.getSeconds();
        return new PyDateTime(year, month, day, hour, minute, second, 0);
    }

    /**
     * @param  {...any} args
     * @returns {PyDateTime}
     */
    static create(...args) {
        const namedArgs = parseArgs(args, [
            "year",
            "month",
            "day",
            "hour",
            "minute",
            "second",
            "microsecond",
        ]);
        const year = namedArgs.year;
        const month = namedArgs.month;
        const day = namedArgs.day;
        const hour = namedArgs.hour ?? 0;
        const minute = namedArgs.minute ?? 0;
        const second = namedArgs.second ?? 0;
        const microsecond = namedArgs.microsecond ?? 0;
        return new PyDateTime(year, month, day, hour, minute, second, microsecond);
    }

    /**
     * @param  {...any} args
     * @returns {PyDateTime}
     */
    static combine(...args) {
        const { date, time } = parseArgs(args, ["date", "time"]);
        return PyDateTime.create(
            date.year,
            date.month,
            date.day,
            time.hour,
            time.minute,
            time.second,
        );
    }

    /**
     * @param {number} year
     * @param {number} month
     * @param {number} day
     * @param {number} hour
     * @param {number} minute
     * @param {number} second
     * @param {number} microsecond
     */
    constructor(year, month, day, hour, minute, second, microsecond) {
        this.year = year;
        this.month = month;
        this.day = day;
        this.hour = hour;
        this.minute = minute;
        this.second = second;
        this.microsecond = microsecond;
    }

    /**
     * @param {PyTimeDelta} timedelta
     * @returns {PyDateTime}
     */
    add(timedelta) {
        const s = tmxxx(
            this.year,
            this.month,
            this.day + timedelta.days,
            this.hour,
            this.minute,
            this.second + timedelta.seconds,
            this.microsecond + timedelta.microseconds,
        );
        return new PyDateTime(
            s.year,
            s.month,
            s.day,
            s.hour,
            s.minute,
            s.second,
            s.microsecond,
        );
    }

    /**
     * @param {any} other
     * @returns {boolean}
     */
    isEqual(other) {
        if (!(other instanceof PyDateTime)) {
            return false;
        }
        return (
            this.year === other.year &&
            this.month === other.month &&
            this.day === other.day &&
            this.hour === other.hour &&
            this.minute === other.minute &&
            this.second === other.second &&
            this.microsecond === other.microsecond
        );
    }

    /**
     * @param {string} format
     * @returns {string}
     */
    strftime(format) {
        return format.replace(/%([A-Za-z])/g, (m, c) => {
            switch (c) {
                case "Y":
                    return fmt4(this.year);
                case "m":
                    return fmt2(this.month);
                case "d":
                    return fmt2(this.day);
                case "H":
                    return fmt2(this.hour);
                case "M":
                    return fmt2(this.minute);
                case "S":
                    return fmt2(this.second);
            }
            throw new ValueError(`No known conversion for ${m}`);
        });
    }

    /**
     * @param {PyTimeDelta} timedelta
     * @returns {PyDateTime}
     */
    substract(timedelta) {
        return this.add(timedelta.negate());
    }

    /** @returns {string} */
    toJSON() {
        return this.strftime("%Y-%m-%d %H:%M:%S");
    }

    /** @returns {PyDateTime} */
    to_utc() {
        const d = new Date(
            this.year,
            this.month - 1,
            this.day,
            this.hour,
            this.minute,
            this.second,
        );
        const timedelta = PyTimeDelta.create({
            minutes: d.getTimezoneOffset(),
        });
        return this.add(timedelta);
    }
}

// ─── PyTime ──────────────────────────────────────────────────────────────────

export class PyTime extends PyDate {
    /**
     * @param  {...any} args
     * @returns {PyTime}
     */
    static create(...args) {
        const namedArgs = parseArgs(args, ["hour", "minute", "second"]);
        const hour = namedArgs.hour || 0;
        const minute = namedArgs.minute || 0;
        const second = namedArgs.second || 0;
        return new PyTime(hour, minute, second);
    }

    constructor(hour, minute, second) {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth() + 1;
        const day = now.getDate();
        super(year, month, day);
        this.hour = hour;
        this.minute = minute;
        this.second = second;
    }

    /**
     * @param {string} format
     * @returns {string}
     */
    strftime(format) {
        return format.replace(/%([A-Za-z])/g, (m, c) => {
            switch (c) {
                case "Y":
                    return fmt4(this.year);
                case "m":
                    return fmt2(this.month + 1);
                case "d":
                    return fmt2(this.day);
                case "H":
                    return fmt2(this.hour);
                case "M":
                    return fmt2(this.minute);
                case "S":
                    return fmt2(this.second);
            }
            throw new ValueError(`No known conversion for ${m}`);
        });
    }

    toJSON() {
        return this.strftime("%H:%M:%S");
    }
}

// ─── PyRelativeDelta ─────────────────────────────────────────────────────────

/*
 * This list is intended to be of that shape (32 days in december), it is used by
 * the algorithm that computes "relativedelta yearday". The algorithm was adapted
 * from the one in python (https://github.com/dateutil/dateutil/blob/2.7.3/dateutil/relativedelta.py#L199)
 */
const DAYS_IN_YEAR = [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 366];

const TIME_PERIODS = ["hour", "minute", "second"];
const PERIODS = ["year", "month", "day", ...TIME_PERIODS];

const RELATIVE_KEYS =
    "years months weeks days hours minutes seconds microseconds leapdays".split(" ");
const ABSOLUTE_KEYS =
    "year month day hour minute second microsecond weekday nlyearday yearday".split(
        " ",
    );

const argsSpec = ["dt1", "dt2"]; // all other arguments are kwargs
export class PyRelativeDelta {
    /**
     * @param  {...any} args
     * @returns {PyRelativeDelta}
     */
    static create(...args) {
        const params = parseArgs(args, argsSpec);
        if ("dt1" in params) {
            throw new Error("relativedelta(dt1, dt2) is not supported for now");
        }
        for (const period of PERIODS) {
            if (period in params) {
                const val = params[period];
                assert(val >= 0, `${period} ${val} is out of range`);
            }
        }

        for (const key of RELATIVE_KEYS) {
            params[key] = params[key] || 0;
        }
        for (const key of ABSOLUTE_KEYS) {
            params[key] = key in params ? params[key] : null;
        }
        params.days += 7 * params.weeks;

        let yearDay = 0;
        if (params.nlyearday) {
            yearDay = params.nlyearday;
        } else if (params.yearday) {
            yearDay = params.yearday;
            if (yearDay > 59) {
                params.leapDays = -1;
            }
        }

        if (yearDay) {
            for (let monthIndex = 0; monthIndex < DAYS_IN_YEAR.length; monthIndex++) {
                if (yearDay <= DAYS_IN_YEAR[monthIndex]) {
                    params.month = monthIndex + 1;
                    if (monthIndex === 0) {
                        params.day = yearDay;
                    } else {
                        params.day = yearDay - DAYS_IN_YEAR[monthIndex - 1];
                    }
                    break;
                }
            }
        }

        return new PyRelativeDelta(params);
    }

    /**
     * @param {PyDateTime|PyDate} date
     * @param {PyRelativeDelta} delta
     * @returns {PyDateTime|PyDate}
     */
    static add(date, delta) {
        if (!(date instanceof PyDate || date instanceof PyDateTime)) {
            throw new NotSupportedError();
        }

        // First pass: determine target year and whether to apply leap days
        const s = tmxxx(
            (delta.year ?? date.year) + delta.years,
            (delta.month ?? date.month) + delta.months,
            delta.day ?? date.day,
            delta.hour ?? /** @type {any} */ (date).hour ?? 0,
            delta.minute ?? /** @type {any} */ (date).minute ?? 0,
            delta.second ?? /** @type {any} */ (date).second ?? 0,
            delta.microsecond ?? /** @type {any} */ (date).microsecond ?? 0,
        );

        const newDateTime = new PyDateTime(
            s.year,
            s.month,
            s.day,
            s.hour,
            s.minute,
            s.second,
            s.microsecond,
        );

        let leapDays = 0;
        if (delta.leapDays && newDateTime.month > 2 && isLeap(newDateTime.year)) {
            leapDays = delta.leapDays;
        }

        // Second pass: apply day and time deltas
        const temp = newDateTime.add(
            PyTimeDelta.create({
                days: delta.days + leapDays,
                hours: delta.hours,
                minutes: delta.minutes,
                seconds: delta.seconds,
                microseconds: delta.microseconds,
            }),
        );

        // Determine return type from input type and actual time values
        const hasTime = Boolean(
            temp.hour || temp.minute || temp.second || temp.microsecond,
        );
        const returnDate =
            !hasTime && date instanceof PyDate
                ? new PyDate(temp.year, temp.month, temp.day)
                : temp;

        // Final pass: target the wanted day of the week (if necessary)
        if (delta.weekday !== null) {
            const wantedDow = delta.weekday + 1; // python: Monday is 0 ; JS: Monday is 1;
            const _date = new Date(
                returnDate.year,
                returnDate.month - 1,
                returnDate.day,
            );
            const days = (7 - _date.getDay() + wantedDow) % 7;
            return returnDate.add(new PyTimeDelta(days, 0, 0));
        }
        return returnDate;
    }

    /**
     * @param {PyDateTime|PyDate} date
     * @param {PyRelativeDelta} delta
     * @returns {PyDateTime|PyDate}
     */
    static substract(date, delta) {
        return PyRelativeDelta.add(date, delta.negate());
    }

    /**
     * @param {Object} params
     * @param {1|-1} sign
     */
    constructor(params = {}, sign = +1) {
        this.years = sign * params.years;
        this.months = sign * params.months;
        this.days = sign * params.days;
        this.hours = sign * params.hours;
        this.minutes = sign * params.minutes;
        this.seconds = sign * params.seconds;
        this.microseconds = sign * params.microseconds;

        this.leapDays = params.leapDays;

        this.year = params.year;
        this.month = params.month;
        this.day = params.day;
        this.hour = params.hour;
        this.minute = params.minute;
        this.second = params.second;
        this.microsecond = params.microsecond;

        this.weekday = params.weekday;
    }

    /** @returns {PyRelativeDelta} */
    negate() {
        return new PyRelativeDelta(this, -1);
    }

    isEqual(other) {
        // For now we don't do normalization in the constructor (or create method).
        // That is, we only compute the overflows at the time we add or substract.
        // This is why we can't support isEqual for now.
        throw new NotSupportedError();
    }
}
