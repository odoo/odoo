/** @odoo-module **/
const { DateTime } = luxon;
/**
 * Change the method toJSON to return the formated value to send server side.
 */
DateTime.prototype.toJSON = function () {
  return this.setLocale("en").toFormat("yyyy-MM-dd HH:mm:ss");
};
export function formatDateTime(value, options = {}) {
  if (value === false) {
    return "";
  }
  if (options.timezone === undefined || options.timezone) {
    value = value.minus({ minutes: value.toJSDate().getTimezoneOffset() });
  }
  return options.format ? value.toFormat(options.format) : value.toJSON();
}
const stripAlphaDupesRegex = /([a-zA-Z])(?<=\1[^\1])/g;
function stripAlphaDupes(str) {
  // Removes any duplicated alphabetic characters in a given string.
  // Example: "aa-bb-CCcc-ddD xxxx-Yy-ZZ" -> "a-b-Cc-dD x-Yy-Z"
  return str.replace(stripAlphaDupesRegex, "");
}
function check(d) {
  // FYI, luxon authorizes years until 275760 included...
  return d.isValid && d.year < 10000 && d;
}
const nonAlphaRegex = /\W/g;
const nonDigitsRegex = /\D/g;
/**
 * Utilitary method to create a Luxon DateTime object.
 * The value can also take the form of a smart date: e.g. "+3w" for three weeks from now.
 * If value can not be parsed with the localized format, the fallback is ISO8601 format.
 *
 * @param {string} value
 * @param {string} [options.format=ISO8601]
 * @param {boolean} [options.timezone=false] parse the date then apply the timezone offset
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
  } else if (!options.format) {
    result = DateTime.fromISO(value);
  } else {
    const fmt = options.format;
    const fmtWoZero = stripAlphaDupes(fmt);
    // Luxon is not permissive regarding non alphabetical characters for
    // formatting strings. So if the value to parse has less characters than
    // the format, we would try to parse without the separating characters.
    const woSeps = value.length < fmt.length && {
      val: value.replace(nonDigitsRegex, ""),
      fmt: fmt.replace(nonAlphaRegex, ""),
    };
    result =
      check(DateTime.fromFormat(value, fmt)) ||
      check(DateTime.fromFormat(value, fmtWoZero)) ||
      (woSeps &&
        (check(DateTime.fromFormat(woSeps.val, woSeps.fmt)) ||
          check(DateTime.fromFormat(woSeps.val, woSeps.fmt.slice(0, woSeps.val.length))))) ||
      DateTime.fromISO(value) || // last try: ISO8601
      DateTime.invalid("mandatory but unused string");
  }
  return options.timezone
    ? result.minus({ minutes: result.toJSDate().getTimezoneOffset() })
    : result;
}
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
const normalize_format_table = {
  // Python strftime to luxon.js conversion table
  // See openerp/addons/base/views/res_lang_views.xml
  // for details about supported directives
  a: "ccc",
  A: "cccc",
  b: "LLL",
  B: "LLLL",
  d: "dd",
  H: "HH",
  I: "hh",
  j: "o",
  m: "LL",
  M: "mm",
  p: "a",
  S: "ss",
  W: "WW",
  w: "c",
  y: "yy",
  Y: "yyyy",
  c: "ccc LLL d HH:mm:ss yyyy",
  x: "LL/dd/yy",
  X: "HH:mm:ss",
};
const _normalize_format_cache = {};
/**
 * Convert Python strftime to escaped luxon.js format.
 *
 * @param {String} value original format
 * @returns {String} valid Luxon format
 */
export function strftimeToLuxonFormat(value) {
  if (_normalize_format_cache[value] === undefined) {
    const isletter = /[a-zA-Z]/,
      output = [];
    let inToken = false;
    for (let index = 0; index < value.length; ++index) {
      let character = value[index];
      if (character === "%" && !inToken) {
        inToken = true;
        continue;
      }
      if (isletter.test(character)) {
        if (inToken && normalize_format_table[character] !== undefined) {
          character = normalize_format_table[character];
        } else {
          character = "[" + character + "]"; // moment.js escape
        }
      }
      output.push(character);
      inToken = false;
    }
    _normalize_format_cache[value] = output.join("");
  }
  return _normalize_format_cache[value];
}
