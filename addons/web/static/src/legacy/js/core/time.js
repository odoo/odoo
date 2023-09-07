/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";

/**
 * Left-pad provided arg 1 with zeroes until reaching size provided by second
 * argument.
 *
 * @param {number|string} str value to pad
 * @param {number} size size to reach on the final padded value
 * @returns {string} padded string
 */
function lpad(str, size) {
    str = "" + str;
    return new Array(size - str.length + 1).join('0') + str;
}
/**
 * @see lpad
 *
 * @param {string} str
 * @param {number} size
 * @returns {string}
 */
function rpad(str, size) {
    str = "" + str;
    return str + new Array(size - str.length + 1).join('0');
}

/**
 * Replacer function for JSON.stringify, serializes Date objects to UTC
 * datetime in the OpenERP Server format.
 *
 * However, if a serialized value has a toJSON method that method is called
 * *before* the replacer is invoked. Date#toJSON exists, and thus the value
 * passed to the replacer is a string, the original Date has to be fetched
 * on the parent object (which is provided as the replacer's context).
 *
 * @param {String} k
 * @param {Object} v
 * @returns {Object}
 */
export function date_to_utc (k, v) {
    var value = this[k];
    if (!(value instanceof Date)) { return v; }

    return datetime_to_str(value);
}

/**
 * Converts a string to a Date javascript object using OpenERP's
 * datetime string format (exemple: '2011-12-01 15:12:35.832').
 *
 * The time zone is assumed to be UTC (standard for OpenERP 6.1)
 * and will be converted to the browser's time zone.
 *
 * @param {String} str A string representing a datetime.
 * @returns {Date}
 */
export function str_to_datetime (str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d(?:\.(\d+))?)$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid datetime");
    }
    var tmp = new Date(2000,0,1);
    tmp.setUTCMonth(1970);
    tmp.setUTCMonth(0);
    tmp.setUTCDate(1);
    tmp.setUTCFullYear(parseFloat(res[1]));
    tmp.setUTCMonth(parseFloat(res[2]) - 1);
    tmp.setUTCDate(parseFloat(res[3]));
    tmp.setUTCHours(parseFloat(res[4]));
    tmp.setUTCMinutes(parseFloat(res[5]));
    tmp.setUTCSeconds(parseFloat(res[6]));
    tmp.setUTCSeconds(parseFloat(res[6]));
    tmp.setUTCMilliseconds(parseFloat(rpad((res[7] || "").slice(0, 3), 3)));
    return tmp;
}

/**
 * Converts a string to a Date javascript object using OpenERP's
 * date string format (exemple: '2011-12-01').
 *
 * As a date is not subject to time zones, we assume it should be
 * represented as a Date javascript object at 00:00:00 in the
 * time zone of the browser.
 *
 * @param {String} str A string representing a date.
 * @returns {Date}
 */
export function str_to_date (str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d\d\d)-(\d\d)-(\d\d)$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid date");
    }
    var tmp = new Date(2000,0,1);
    tmp.setFullYear(parseFloat(res[1]));
    tmp.setMonth(parseFloat(res[2]) - 1);
    tmp.setDate(parseFloat(res[3]));
    tmp.setHours(0);
    tmp.setMinutes(0);
    tmp.setSeconds(0);
    return tmp;
}

/**
 * Converts a string to a Date javascript object using OpenERP's
 * time string format (exemple: '15:12:35').
 *
 * The OpenERP times are supposed to always be naive times. We assume it is
 * represented using a javascript Date with a date 1 of January 1970 and a
 * time corresponding to the meant time in the browser's time zone.
 *
 * @param {String} str A string representing a time.
 * @returns {Date}
 */
export function str_to_time (str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d):(\d\d):(\d\d(?:\.(\d+))?)$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid time");
    }
    var tmp = new Date();
    tmp.setFullYear(1970);
    tmp.setMonth(0);
    tmp.setDate(1);
    tmp.setHours(parseFloat(res[1]));
    tmp.setMinutes(parseFloat(res[2]));
    tmp.setSeconds(parseFloat(res[3]));
    tmp.setMilliseconds(parseFloat(rpad((res[4] || "").slice(0, 3), 3)));
    return tmp;
}

/**
 * Converts a Date javascript object to a string using OpenERP's
 * datetime string format (exemple: '2011-12-01 15:12:35').
 *
 * The time zone of the Date object is assumed to be the one of the
 * browser and it will be converted to UTC (standard for OpenERP 6.1).
 *
 * @param {Date} obj
 * @returns {String} A string representing a datetime.
 */
export function datetime_to_str (obj) {
    if (!obj) {
        return false;
    }
    return lpad(obj.getUTCFullYear(),4) + "-" + lpad(obj.getUTCMonth() + 1,2) + "-"
         + lpad(obj.getUTCDate(),2) + " " + lpad(obj.getUTCHours(),2) + ":"
         + lpad(obj.getUTCMinutes(),2) + ":" + lpad(obj.getUTCSeconds(),2);
}

/**
 * Converts a Date javascript object to a string using OpenERP's
 * date string format (exemple: '2011-12-01').
 *
 * As a date is not subject to time zones, we assume it should be
 * represented as a Date javascript object at 00:00:00 in the
 * time zone of the browser.
 *
 * @param {Date} obj
 * @returns {String} A string representing a date.
 */
export function date_to_str (obj) {
    if (!obj) {
        return false;
    }
    return lpad(obj.getFullYear(),4) + "-" + lpad(obj.getMonth() + 1,2) + "-"
         + lpad(obj.getDate(),2);
}

/**
 * Converts a Date javascript object to a string using OpenERP's
 * time string format (exemple: '15:12:35').
 *
 * The OpenERP times are supposed to always be naive times. We assume it is
 * represented using a javascript Date with a date 1 of January 1970 and a
 * time corresponding to the meant time in the browser's time zone.
 *
 * @param {Date} obj
 * @returns {String} A string representing a time.
 */
export function time_to_str (obj) {
    if (!obj) {
        return false;
    }
    return lpad(obj.getHours(),2) + ":" + lpad(obj.getMinutes(),2) + ":"
         + lpad(obj.getSeconds(),2);
}

export function auto_str_to_date (value) {
    try {
        return str_to_datetime(value);
    } catch {}
    try {
        return str_to_date(value);
    } catch {}
    try {
        return str_to_time(value);
    } catch {}
    throw new Error(_t("'%s' is not a correct date, datetime nor time", value));
}

export function auto_date_to_str (value, type) {
    switch(type) {
        case 'datetime':
            return datetime_to_str(value);
        case 'date':
            return date_to_str(value);
        case 'time':
            return time_to_str(value);
        default:
            throw new Error(_t("'%s' is not convertible to date, datetime nor time", type));
    }
}

const luxonToMomentFormatTable = {
    c: "d",
    d: "D",
    o: "DDDD",
    a: "A",
    y: "Y",
};

function luxonToMomentFormat(format) {
    return format.replace(/[a-zA-Z]/g, (match) => luxonToMomentFormatTable[match] || match);
}

/**
 * Get date format of the user's language
 */
export function getLangDateFormat() {
    return luxonToMomentFormat(localization.dateFormat);
}

/**
 * Get time format of the user's language
 */
export function getLangTimeFormat() {
    return luxonToMomentFormat(localization.timeFormat);
}

/**
 * Get date time format of the user's language
 */
export function getLangDatetimeFormat() {
    return luxonToMomentFormat(localization.dateTimeFormat);
}

const dateFormatWoZeroCache = {};
/**
 * Get date format of the user's language - allows non padded
 */
export function getLangDateFormatWoZero() {
    const dateFormat = getLangDateFormat();
    if (!(dateFormat in dateFormatWoZeroCache)) {
        dateFormatWoZeroCache[dateFormat] = dateFormat
            .replace('MM', 'M')
            .replace('DD', 'D');
    }
    return dateFormatWoZeroCache[dateFormat];
}

const timeFormatWoZeroCache = {};
/**
 * Get time format of the user's language - allows non padded
 */
export function getLangTimeFormatWoZero() {
    const timeFormat = getLangTimeFormat();
    if (!(timeFormat in timeFormatWoZeroCache)) {
        timeFormatWoZeroCache[timeFormat] = timeFormat
            .replace('HH', 'H')
            .replace('mm', 'm')
            .replace('ss', 's');
    }
    return timeFormatWoZeroCache[timeFormat];
}

export default {
    date_to_utc: date_to_utc,
    str_to_datetime: str_to_datetime,
    str_to_date: str_to_date,
    str_to_time: str_to_time,
    datetime_to_str: datetime_to_str,
    date_to_str: date_to_str,
    time_to_str: time_to_str,
    auto_str_to_date: auto_str_to_date,
    auto_date_to_str: auto_date_to_str,
    getLangDateFormat: getLangDateFormat,
    getLangTimeFormat: getLangTimeFormat,
    getLangDateFormatWoZero: getLangDateFormatWoZero,
    getLangTimeFormatWoZero: getLangTimeFormatWoZero,
    getLangDatetimeFormat: getLangDatetimeFormat,
};
