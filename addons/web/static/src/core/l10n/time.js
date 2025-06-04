import { localization } from "@web/core/l10n/localization";

const { DateTime } = luxon;

const NUMERAL_MAPS = [
    "٠١٢٣٤٥٦٧٨٩", // Arabic
    "۰۱۲۳۴۵۶۷۸۹",
    "०१२३४५६७८९", // Devanagari (Hindi)
    "๑๒๓๔๕๖๗๘๙๐", // Thai
    "零一二三四五六七八九", // Chinese/Japanese/Korean
];

/**
 * A representation of a specific time in a 24 hour format
 */
export class Time {
    /**
     * This method will return a Time object contructed
     * differently depending on the type of {value}
     *
     * - If value is already a Time object, it returns it.
     * - If value is null, undefined or false, it returns null.
     * - If value is a string, it will try to parse it, @see {parseTime}
     * - If value is an object, it will use its [hour], [minute] and [second] properties
     * - Otherwise, return a new Time with default values
     *
     * @param {any} value
     * @returns {Time|null}
     */
    static from(value) {
        if (value === null || value === undefined || value === false) {
            return null;
        } else if (value instanceof Time) {
            return value;
        } else if (typeof value === "string") {
            return parseTime(value, true);
        } else if (typeof value === "object") {
            return new Time(value);
        } else {
            return null;
        }
    }

    /**
     * @param {{
     *  hour: 0,
     *  minute: 0,
     *  second: 0,
     * }?} params
     */
    constructor({ hour = 0, minute = 0, second = 0 } = {}) {
        /**@type {number} */
        this.hour = hour;
        /**@type {number} */
        this.minute = minute;
        /**@type {number} */
        this.second = second;

        /**
         * @private
         * @type {boolean}
         */
        this._is24HourFormat = is24HourFormat();

        /**
         * @private
         * @type {boolean}
         */
        this._isMeridiemFormat = isMeridiemFormat();
    }

    /**
     * @param {number} rounding
     */
    roundMinutes(rounding) {
        this.minute = Math.round(this.minute / rounding) * rounding;
    }

    /**
     * @returns {Time}
     */
    copy() {
        return new Time(this);
    }

    /**
     * @param {Time} other
     * @param {boolean} [checkSeconds=false]
     * @returns {boolean}
     */
    equals(other, checkSeconds = false) {
        return (
            other &&
            this.hour === other.hour &&
            this.minute === other.minute &&
            (!checkSeconds || this.second === other.second)
        );
    }

    /**
     * Returns the formatted value of the time, with 24 of 12 hours
     * format and with or without meridiems depending on the current
     * localization time format.
     *
     * @param {boolean} [showSeconds=false]
     * @returns {string}
     */
    toString(showSeconds = false) {
        const hourFormat = this._is24HourFormat ? "H" : "h";
        const secondFormat = showSeconds ? ":ss" : "";
        const meridiemFormat = this._isMeridiemFormat ? "a" : "";
        return this.toDateTime()
            .toFormat(`${hourFormat}:mm${secondFormat}${meridiemFormat}`)
            .toLowerCase();
    }

    /**
     * @returns {DateTime}
     */
    toDateTime() {
        return DateTime.fromObject(this.toObject());
    }

    /**
     * Returns the time as an Object
     * @returns {{hour: number, minute: number, second: number}}
     */
    toObject() {
        return {
            hour: this.hour,
            minute: this.minute,
            second: this.second,
        };
    }
}

/**
 * Returns whether the given format is a 24-hour format.
 * Falls back to localization time format if none is given.
 *
 * @param {string} format
 */
export function is24HourFormat(format) {
    return /H/.test(format || localization.timeFormat);
}

/**
 * Returns whether the given format uses a meridiem suffix (AM/PM).
 * Falls back to localization time format if none is given.
 *
 * @param {string} format
 */
export function isMeridiemFormat(format) {
    return /a/.test(format || localization.timeFormat);
}

/**
 * Tries to parse a Time object from a time string
 * representation such as:
 * "10:15"  -> 10:15:00
 * "2h5"    -> 02:50:00
 * "1015"   -> 10:15:00
 * "125"    -> 12:50:00
 * "315"    -> 03:15:00
 * "5:15pm" -> 17:15:00
 *
 * Returns null if the value could not be parsed.
 *
 * @param {string} value
 * @param {boolean} [parseSeconds]
 * @returns {Time | null}
 */
export function parseTime(value, parseSeconds) {
    const { isPm, isAm } = meridiemCheck(value);
    value = normalizeTimeStr(value);

    if (!value) {
        return null;
    }

    let hour = 0;
    let minute = 0;
    let second = 0;

    const parse = (str) => {
        if (str.length === 0) {
            return 0;
        } else if (/^[\d]+$/.test(str)) {
            return parseInt(str, 10);
        } else {
            return NaN;
        }
    };

    const parts = value.split(/[\s:]/g);
    if (parts.length > 3) {
        return null;
    } else if (parts.length === 3) {
        if (!parseSeconds) {
            return null;
        }
        hour = parse(parts[0]);
        minute = parse(parts[1].padEnd(2, "0"));
        second = parse(parts[2].padEnd(2, "0"));
    } else if (parts.length === 2) {
        hour = parse(parts[0]);
        minute = parse(parts[1].padEnd(2, "0"));
    } else if (parts.length === 1) {
        const raw = parts[0];

        const pickSolution = (...solutions) => {
            for (const solution of solutions) {
                const h = parse(solution[0]);
                if (h <= 24) {
                    hour = h;
                    if (solution[1]) {
                        minute = parse(solution[1].padEnd(2, "0"));
                    }
                    break;
                }
            }
        };

        if (raw.length == 1) {
            hour = parse(raw);
        } else if (raw.length == 2) {
            pickSolution([raw], [raw[0], raw[1]]);
        } else if (raw.length === 3) {
            pickSolution([raw.slice(0, 2), raw[2]], [raw[0], raw.slice(1)]);
        } else if (raw.length === 4) {
            hour = parse(raw.slice(0, 2));
            minute = parse(raw.slice(2));
        } else if (raw.length > 4 && raw.length <= 6) {
            if (!parseSeconds) {
                return null;
            }
            hour = parse(raw.slice(0, 2));
            minute = parse(raw.slice(2, 4));
            second = parse(raw.slice(4).padEnd(2, "0"));
        } else {
            return null;
        }
    }

    if (isPm && hour < 12) {
        hour += 12;
    } else if (isAm && hour === 12) {
        hour = 0;
    }

    if (hour >= 0 && hour <= 24 && minute >= 0 && minute < 60 && second >= 0 && second < 60) {
        if (hour === 24) {
            hour = 0;
        }
        return new Time({ hour, minute, second });
    } else {
        return null;
    }
}

/**
 * - Converts other languages numeral systems to western arabic numbers
 * - Replaces with ":" all chains of non-numeric characters between numbers
 * - Removes all trailing non-numeric characters
 *
 * @param {string} timeStr
 * @returns {string|false}
 */
function normalizeTimeStr(timeStr) {
    if (typeof timeStr !== "string") {
        return false;
    }

    timeStr = timeStr.trim().toLowerCase();

    for (const map of NUMERAL_MAPS) {
        for (let i = 0; i < map.length; i++) {
            timeStr = timeStr.replaceAll(map[i], i);
        }
    }

    return timeStr.replace(/^\D+|\D+$/g, "").replace(/\D+/g, ":");
}

/**
 * @param {string} timeStr
 * @returns {{ isPm: boolean, isAm: boolean }}
 */
function meridiemCheck(timeStr) {
    const amPmMatch = typeof timeStr === "string" ? timeStr.toLowerCase().match(/(am|pm)/g) : false;
    return {
        isPm: amPmMatch && amPmMatch[0] === "pm",
        isAm: amPmMatch && amPmMatch[0] === "am",
    };
}
