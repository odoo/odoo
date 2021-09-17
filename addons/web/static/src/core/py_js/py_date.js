/** @odoo-module **/

import { parseArgs } from "./py_utils";

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------

export class AssertionError extends Error {}
export class ValueError extends Error {}
export class NotSupportedError extends Error {}

// -----------------------------------------------------------------------------
// helpers
// -----------------------------------------------------------------------------

function fmt2(n) {
    return String(n).padStart(2, "0");
}
function fmt4(n) {
    return String(n).padStart(4, "0");
}

/**
 * computes (Math.floor(a/b), a%b and passes that to the callback.
 *
 * returns the callback's result
 */
function divmod(a, b, fn) {
    let mod = a % b;
    // in python, sign(a % b) === sign(b). Not in JS. If wrong side, add a
    // round of b
    if ((mod > 0 && b < 0) || (mod < 0 && b > 0)) {
        mod += b;
    }
    return fn(Math.floor(a / b), mod);
}

function assert(bool) {
    if (!bool) {
        throw new AssertionError("AssertionError");
    }
}

const DAYS_IN_MONTH = [null, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const DAYS_BEFORE_MONTH = [null];

for (let dbm = 0, i = 1; i < DAYS_IN_MONTH.length; ++i) {
    DAYS_BEFORE_MONTH.push(dbm);
    dbm += DAYS_IN_MONTH[i];
}

function daysInMonth(year, month) {
    if (month === 2 && isLeap(year)) {
        return 29;
    }
    return DAYS_IN_MONTH[month];
}

function isLeap(year) {
    return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function daysBeforeYear(year) {
    const y = year - 1;
    return y * 365 + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400);
}

function daysBeforeMonth(year, month) {
    const postLeapFeb = month > 2 && isLeap(year);
    return DAYS_BEFORE_MONTH[month] + (postLeapFeb ? 1 : 0);
}

function ymd2ord(year, month, day) {
    const dim = daysInMonth(year, month);
    if (!(1 <= day && day <= dim)) {
        throw new ValueError(`day must be in 1..${dim}`);
    }
    return daysBeforeYear(year) + daysBeforeMonth(year, month) + day;
}

const DI400Y = daysBeforeYear(401);
const DI100Y = daysBeforeYear(101);
const DI4Y = daysBeforeYear(5);

function ord2ymd(n) {
    --n;
    let n400, n100, n4, n1, n0;
    divmod(n, DI400Y, function (_n400, n) {
        n400 = _n400;
        divmod(n, DI100Y, function (_n100, n) {
            n100 = _n100;
            divmod(n, DI4Y, function (_n4, n) {
                n4 = _n4;
                divmod(n, 365, function (_n1, n) {
                    n1 = _n1;
                    n0 = n;
                });
            });
        });
    });

    n = n0;
    const year = n400 * 400 + 1 + n100 * 100 + n4 * 4 + n1;
    if (n1 == 4 || n100 == 100) {
        assert(n0 === 0);
        return {
            year: year - 1,
            month: 12,
            day: 31,
        };
    }

    let leapyear = n1 === 3 && (n4 !== 24 || n100 == 3);
    assert(leapyear == isLeap(year));
    let month = (n + 50) >> 5;
    let preceding = DAYS_BEFORE_MONTH[month] + (month > 2 && leapyear ? 1 : 0);
    if (preceding > n) {
        --month;
        preceding -= DAYS_IN_MONTH[month] + (month === 2 && leapyear ? 1 : 0);
    }
    n -= preceding;
    return {
        year: year,
        month: month,
        day: n + 1,
    };
}

/**
 * Converts the stuff passed in into a valid date, applying overflows as needed
 */
function tmxxx(year, month, day, hour, minute, second, microsecond) {
    hour = hour || 0;
    minute = minute || 0;
    second = second || 0;
    microsecond = microsecond || 0;

    if (microsecond < 0 || microsecond > 999999) {
        divmod(microsecond, 1000000, function (carry, ms) {
            microsecond = ms;
            second += carry;
        });
    }
    if (second < 0 || second > 59) {
        divmod(second, 60, function (carry, s) {
            second = s;
            minute += carry;
        });
    }
    if (minute < 0 || minute > 59) {
        divmod(minute, 60, function (carry, m) {
            minute = m;
            hour += carry;
        });
    }
    if (hour < 0 || hour > 23) {
        divmod(hour, 24, function (carry, h) {
            hour = h;
            day += carry;
        });
    }
    // That was easy.  Now it gets muddy:  the proper range for day
    // can't be determined without knowing the correct month and year,
    // but if day is, e.g., plus or minus a million, the current month
    // and year values make no sense (and may also be out of bounds
    // themselves).
    // Saying 12 months == 1 year should be non-controversial.
    if (month < 1 || month > 12) {
        divmod(month - 1, 12, function (carry, m) {
            month = m + 1;
            year += carry;
        });
    }
    // Now only day can be out of bounds (year may also be out of bounds
    // for a datetime object, but we don't care about that here).
    // If day is out of bounds, what to do is arguable, but at least the
    // method here is principled and explainable.
    let dim = daysInMonth(year, month);
    if (day < 1 || day > dim) {
        // Move day-1 days from the first of the month.  First try to
        // get off cheap if we're only one day out of range (adjustments
        // for timezone alone can't be worse than that).
        if (day === 0) {
            --month;
            if (month > 0) {
                day = daysInMonth(year, month);
            } else {
                --year;
                month = 12;
                day = 31;
            }
        } else if (day == dim + 1) {
            ++month;
            day = 1;
            if (month > 12) {
                month = 1;
                ++year;
            }
        } else {
            let r = ord2ymd(ymd2ord(year, month, 1) + (day - 1));
            year = r.year;
            month = r.month;
            day = r.day;
        }
    }
    return {
        year: year,
        month: month,
        day: day,
        hour: hour,
        minute: minute,
        second: second,
        microsecond: microsecond,
    };
}

// -----------------------------------------------------------------------------
// Date/Time and related classes
// -----------------------------------------------------------------------------

export class PyDate {
    /**
     * @returns {PyDate}
     */
    static today() {
        const now = new Date();
        const year = now.getUTCFullYear();
        const month = now.getUTCMonth() + 1;
        const day = now.getUTCDate();
        return new PyDate(year, month, day);
    }

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

    toJSON() {
        return this.strftime("%Y-%m-%d");
    }
}

export class PyDateTime {
    /**
     * @returns {PyDateTime}
     */
    static now() {
        const now = new Date();
        const year = now.getUTCFullYear();
        const month = now.getUTCMonth() + 1;
        const day = now.getUTCDate();
        const hour = now.getUTCHours();
        const minute = now.getUTCMinutes();
        const second = now.getUTCSeconds();
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
        const hour = namedArgs.hour || 0;
        const minute = namedArgs.minute || 0;
        const second = namedArgs.second || 0;
        const ms = namedArgs.micro / 1000 || 0;
        return new PyDateTime(year, month, day, hour, minute, second, ms);
    }

    /**
     * @param  {...any} args
     * @returns {PyDateTime}
     */
    static combine(...args) {
        const { date, time } = parseArgs(args, ["date", "time"]);
        // not sure. should we go through constructor instead? what about args normalization?
        return PyDateTime.create(
            date.year,
            date.month,
            date.day,
            time.hour,
            time.minute,
            time.second
        );
    }

    constructor(year, month, day, hour, minute, second, millisecond) {
        this.year = year;
        this.month = month; // 1-indexed => 1 = january, 2 = february, ...
        this.day = day; // 1-indexed => 1 = first day of month, ...
        this.hour = hour;
        this.minute = minute;
        this.second = second;
        this.millisecond = millisecond;
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

    toJSON() {
        return this.strftime("%Y-%m-%d %H:%M:%S");
    }

    to_utc() {
        const d = new Date(this.year, this.month, this.day, this.hour, this.minute, this.second);
        const offset = d.getTimezoneOffset();
        // previous implementation did use timedelta
        const s = tmxxx(
            this.year,
            this.month,
            this.day,
            this.hour,
            this.minute,
            this.second + 60 * offset
        );
        return new PyDateTime(s.year, s.month, s.day, s.hour, s.minute, s.second);
    }
}

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
        const month = now.getUTCMonth();
        const day = now.getUTCDate();
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

const argsSpec = "year month day hour minute second years months weeks days hours minutes seconds weekday".split(
    " "
);

export class PyRelativeDelta {
    /**
     * @param  {...any} args
     * @returns {PyRelativeDelta}
     */
    static create(...args) {
        const delta = new PyRelativeDelta();
        const namedArgs = parseArgs(args, argsSpec);
        delta.year = (namedArgs.year || 0) + (namedArgs.years || 0);
        delta.month = (namedArgs.month || 0) + (namedArgs.months || 0);
        delta.day = (namedArgs.day || 0) + (namedArgs.days || 0);
        delta.hour = (namedArgs.hour || 0) + (namedArgs.hours || 0);
        delta.minute = (namedArgs.minute || 0) + (namedArgs.minutes || 0);
        delta.second = (namedArgs.second || 0) + (namedArgs.seconds || 0);
        delta.day += 7 * (namedArgs.weeks || 0);
        if (namedArgs.weekday) {
            throw new NotSupportedError("weekday is not supported");
        }
        return delta;
    }

    /**
     * @param {PyDate} date
     * @param {PyRelativeDelta} delta
     * @returns {PyDateTime}
     */
    static add(date, delta) {
        const s = tmxxx(
            date.year,
            date.month,
            date.day + delta.day,
            delta.hour,
            delta.minute,
            delta.second
        );
        return new PyDateTime(s.year, s.month, s.day, s.hour, s.minute, s.second, 0);
    }

    /**
     * @param {PyDate} date
     * @param {PyRelativeDelta} delta
     * @returns {PyDateTime}
     */
    static substract(date, delta) {
        const s = tmxxx(
            date.year,
            date.month,
            date.day - delta.day,
            -delta.hour,
            -delta.minute,
            -delta.second
        );
        return new PyDateTime(s.year, s.month, s.day, s.hour, s.minute, s.second, 0);
    }

    constructor() {
        this.year = 0;
        this.month = 0;
        this.day = 0;
        this.hour = 0;
        this.minute = 0;
        this.second = 0;
    }
}
