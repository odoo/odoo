/** @odoo-module **/

import { browser } from "../core/browser";
import { serviceRegistry } from "../webclient/service_registry";
import { localization } from "./localization_settings";
import { translatedTerms } from "./translation";

const normalizeFormatTable = {
  // Python strftime to luxon.js conversion table
  // See openerp/addons/base/views/res_lang_views.xml
  // for details about supported directives
  a: "ccc",
  A: "cccc",
  b: "MMM",
  B: "MMMM",
  d: "dd",
  H: "HH",
  I: "hh",
  j: "o",
  m: "MM",
  M: "mm",
  p: "a",
  S: "ss",
  W: "WW",
  w: "c",
  y: "yy",
  Y: "yyyy",
  c: "ccc MMM d HH:mm:ss yyyy",
  x: "MM/dd/yy",
  X: "HH:mm:ss",
};

const _normalize_format_cache = {};

/**
 * Convert Python strftime to escaped luxon.js format.
 *
 * @param {string} value original format
 * @returns {string} valid Luxon format
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
        if (inToken && normalizeFormatTable[character] !== undefined) {
          character = normalizeFormatTable[character];
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

export const localizationService = {
  dependencies: ["user"],
  deploy: async (env) => {
    const cacheHashes = odoo.session_info.cache_hashes;
    const translationsHash = cacheHashes.translations || new Date().getTime().toString();
    const lang = env.services.user.lang || null;
    let url = `/wowl/localization/${translationsHash}`;
    if (lang) {
      url += `?lang=${lang}`;
    }

    const response = await browser.fetch(url);
    if (!response.ok) {
      throw new Error("Error while fetching translations");
    }
    const { lang_params: userLocalization, terms } = await response.json();

    Object.setPrototypeOf(translatedTerms, terms);
    function _t(str) {
      return terms[str] || str;
    }
    env._t = _t;
    env.qweb.translateFn = _t;
    const dateFormat = strftimeToLuxonFormat(userLocalization.date_format);
    const timeFormat = strftimeToLuxonFormat(userLocalization.time_format);
    const dateTimeFormat = `${dateFormat} ${timeFormat}`;
    const grouping = JSON.parse(userLocalization.grouping);

    Object.assign(localization, {
      dateFormat,
      timeFormat,
      dateTimeFormat,
      decimalPoint: userLocalization.decimal_point,
      direction: userLocalization.direction,
      grouping,
      multiLang: userLocalization.multi_lang,
      thousandsSep: userLocalization.thousands_sep,
      weekStart: userLocalization.week_start,
    });
  },
};

serviceRegistry.add("localization", localizationService);
