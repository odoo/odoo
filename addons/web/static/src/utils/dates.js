/** @odoo-module **/

import { localization } from "../localization/localization_settings";
import { _lt } from "../localization/translation";
import { sprintf } from "./strings";

/** @type {any} */
const { DateTime } = luxon;

/**
 * Change the method toJSON to return the formated value to send server side.
 */
DateTime.prototype.toJSON = function () {
  return this.setLocale("en").toFormat("yyyy-MM-dd HH:mm:ss");
};

// -----------------------------------------------------------------------------

/**
 * Format a DateTime object
 *
 * @param {DateTime | false} value
 * @param {{format?: string, timezone?: boolean}} options
 * @returns {string}
 */
export function formatDateTime(value, options = {}) {
  if (value === false) {
    return "";
  }
  const timezone = "timezone" in options ? options.timezone : true;
  const format = "format" in options ? options.format : localization.dateTimeFormat;

  if (timezone) {
    value = value.minus({ minutes: value.toJSDate().getTimezoneOffset() });
  }
  return value.toFormat(format);
}

// -----------------------------------------------------------------------------

/**
 * @param {string} str
 * @returns {string}
 */
function stripAlphaDupes(str) {
  // Removes any duplicated alphabetic characters in a given string.
  // Example: "aa-bb-CCcc-ddD xxxx-Yy-ZZ" -> "a-b-Cc-dD x-Yy-Z"
  return str.replace(/[a-zA-Z]/g, (letter, index, str) => {
    return letter === str[index - 1] ? "" : letter;
  });
}

/**
 * FIXME: signature looks wrong
 *
 * @param {DateTime | false} date
 * @returns {boolean}
 */
function check(date) {
  // FYI, luxon authorizes years until 275760 included...
  return date.isValid && date.year < 10000 && date;
}

const nonAlphaRegex = /\W/g;
const nonDigitsRegex = /\D/g;

/**
 * Utility method to create a Luxon DateTime object.
 * The value can also take the form of a smart date: e.g. "+3w" for three weeks
 * from now. If value can not be parsed with the localized format, the fallback
 * is ISO8601 format.
 *
 * @param {string} value
 * @param {{format?: string, timezone?: boolean}} options
 * @param {string} [options.format] default value is ISO8601
 * @param {boolean} [options.timezone] parse the date then apply the timezone
 *    offset. Default=false
 * @returns {DateTime|false} Luxon DateTime object
 */
export function parseDateTime(value, options = {}) {
  if (!value) {
    return false;
  }
  let result;
  const smartDate = parseSmartDateInput(value);
  if (smartDate) {
    result = smartDate;
  } else {
    const fmt = options.format || localization.dateTimeFormat;
    const fmtWoZero = stripAlphaDupes(fmt);
    // Luxon is not permissive regarding non alphabetical characters for
    // formatting strings. So if the value to parse has less characters than
    // the format, we would try to parse without the separating characters.
    const woSeps = value.length < fmt.length && {
      val: value.replace(nonDigitsRegex, ""),
      fmt: fmt.replace(nonAlphaRegex, ""),
    };
    result =
      check(DateTime.fromFormat(value, fmt, { locale: "no" })) ||
      check(DateTime.fromFormat(value, fmtWoZero)) ||
      (woSeps &&
        (check(DateTime.fromFormat(woSeps.val, woSeps.fmt)) ||
          check(DateTime.fromFormat(woSeps.val, woSeps.fmt.slice(0, woSeps.val.length))))) ||
      check(DateTime.fromSQL(value)) ||
      DateTime.fromISO(value) || // last try: ISO8601
      DateTime.invalid("mandatory but unused string");
  }
  const timezone = "timezone" in options ? options.timezone : false;
  if (timezone) {
    result = result.minus({ minutes: result.toJSDate().getTimezoneOffset() });
  }

  if (result && !result.isValid) {
    throw new Error(sprintf(_lt("'%s' is not a correct date or datetime").toString(), value));
  }
  return result;
}

export function parseDate(value, options = {}) {
  return parseDateTime(value, {
    format: localization.dateFormat,
    timezone: options.timezone,
  });
}
// -----------------------------------------------------------------------------

const dateUnits = {
  d: "days",
  m: "months",
  w: "weeks",
  y: "years",
};

const smartDateRegex = new RegExp(`^([+-])(\\d+)([${Object.keys(dateUnits).join("")}]?)$`);

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
 * @returns {DateTime|false} Luxon datetime object
 */
export function parseSmartDateInput(value) {
  const match = smartDateRegex.exec(value);
  if (match) {
    let date = DateTime.local();
    const offset = parseInt(match[2], 10);
    const unit = dateUnits[match[3] || "d"];
    if (match[1] === "+") {
      date = date.plus({ [unit]: offset });
    } else {
      date = date.minus({ [unit]: offset });
    }
    return date;
  }
  return false;
}
