/** @odoo-module **/

import time from "@web/legacy/js/core/time";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

function getTimezoneOffset(value) {
    return luxon.Settings.defaultZone.offset(value.valueOf());
}

/**
 * Returns a string representing a date.  If the value is false, then we return
 * an empty string. Note that this is dependant on the localization settings
 *
 * @param {Moment|false} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.timezone=true] use the user timezone when formating the
 *        date
 * @returns {string}
 */
export function formatDate(value, field, options) {
    if (value === false || isNaN(value)) {
        return "";
    }
    if (field && field.type === 'datetime') {
        if (!options || !('timezone' in options) || options.timezone) {
            value = value.clone().add(getTimezoneOffset(value), 'minutes');
        }
    }
    var date_format = time.getLangDateFormat();
    return value.format(date_format);
}

/**
 * Returns a string representing a datetime.  If the value is false, then we
 * return an empty string.  Note that this is dependant on the localization
 * settings
 *
 * @params {Moment|false}
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.timezone=true] use the user timezone when formating the
 *        date
 * @returns {string}
 */
export function formatDateTime(value, field, options) {
    if (value === false) {
        return "";
    }
    if (!options || !('timezone' in options) || options.timezone) {
        value = value.clone().add(getTimezoneOffset(value), 'minutes');
    }
    return value.format(time.getLangDatetimeFormat());
}

/**
 * Smart date inputs are shortcuts to write dates quicker.
 * These shortcuts should respect the format ^[+-]\d+[dmwy]?$
 *
 * e.g.
 *   "+1d" or "+1" will return now + 1 day
 *   "-2w" will return now - 2 weeks
 *   "+3m" will return now + 3 months
 *   "-4y" will return now + 4 years
 *
 * @param {string} value
 * @returns {DateTime|false} luxon DateTime
 */
function parseSmartDateInput(value) {
    const units = {
        d: 'days',
        m: 'months',
        w: 'weeks',
        y: 'years',
    };
    const re = new RegExp(`^([+-])(\\d+)([${Object.keys(units).join('')}]?)$`);
    const match = re.exec(value);
    if (match) {
        let date = DateTime.now()
        const offset = parseInt(match[2], 10);
        const unit = units[match[3] || 'd'];
        if (match[1] === '+') {
            date.plus({[unit]: offset});
        } else {
            date.minus({[unit]: offset});
        }
        return date;
    }
    return false;
}

/**
 * Create an Date object
 * The method toJSON return the formated value to send value server side
 *
 * @param {string} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.isUTC] the formatted date is utc
 * @param {boolean} [options.timezone=false] format the date after apply the timezone
 *        offset
 * @returns {Moment|false} Moment date object
 */
export function parseDate(value, field, options) {
    if (!value) {
        return false;
    }
    var datePattern = time.getLangDateFormat();
    var datePatternWoZero = time.getLangDateFormatWoZero();
    var date;
    const smartDate = parseSmartDateInput(value);
    if (smartDate) {
        date = smartDate;
    } else {
        if (options && options.isUTC) {
            value = value.padStart(10, "0"); // server may send "932-10-10" for "0932-10-10" on some OS
            date = moment.utc(value);
        } else {
            date = moment.utc(value, [datePattern, datePatternWoZero, moment.ISO_8601]);
        }
    }
    if (date.isValid()) {
        if (date.year() === 0) {
            date.year(moment.utc().year());
        }
        if (date.year() >= 1000){
            date.toJSON = function () {
                return this.clone().locale('en').format('YYYY-MM-DD');
            };
            return date;
        }
    }
    throw new Error(_t("'%s' is not a correct date", value));
}

/**
 * Create an Date object
 * The method toJSON return the formated value to send value server side
 *
 * @param {string} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.isUTC] the formatted date is utc
 * @param {boolean} [options.timezone=false] format the date after apply the timezone
 *        offset
 * @returns {Moment|false} Moment date object
 */
export function parseDateTime(value, field, options) {
    if (!value) {
        return false;
    }
    const datePattern = time.getLangDateFormat();
    const timePattern = time.getLangTimeFormat();
    const datePatternWoZero = time.getLangDateFormatWoZero();
    const timePatternWoZero = time.getLangTimeFormatWoZero();
    var pattern1 = datePattern + ' ' + timePattern;
    var pattern2 = datePatternWoZero + ' ' + timePatternWoZero;
    var datetime;
    const smartDate = parseSmartDateInput(value);
    if (smartDate) {
        datetime = smartDate;
    } else {
        if (options && options.isUTC) {
            value = value.padStart(19, "0"); // server may send "932-10-10" for "0932-10-10" on some OS
            // phatomjs crash if we don't use this format
            datetime = moment.utc(value.replace(' ', 'T') + 'Z');
        } else {
            datetime = moment.utc(value, [pattern1, pattern2, moment.ISO_8601]);
            if (options && options.timezone) {
                datetime.add(-getTimezoneOffset(datetime), 'minutes');
            }
        }
    }
    if (datetime.isValid()) {
        if (datetime.year() === 0) {
            datetime.year(moment.utc().year());
        }
        if (datetime.year() >= 1000) {
            datetime.toJSON = function () {
                return this.clone().locale('en').format('YYYY-MM-DD HH:mm:ss');
            };
            return datetime;
        }
    }
    throw new Error(_t("'%s' is not a correct datetime", value));
}
