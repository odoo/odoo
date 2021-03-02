/** @odoo-module **/

import * as dates from "../utils/dates";
import * as numbers from "../utils/numbers";
import { escapeRegExp, sprintf } from "../utils/strings";
import { serviceRegistry } from "../webclient/service_registry";

const translatedTerms = {};

/**
 * Eager translation function, performs translation immediately at call.
 */
function _t(str) {
  return translatedTerms[str] || str;
}

/**
 * Lazy translation function, only performs the translation when actually
 * printed (e.g. inserted into a template).
 * Useful when defining translatable strings in code evaluated before the
 * translations are loaded, as class attributes or at the top-level of
 * an Odoo Web module
 */
export function _lt(str) {
  return { toString: () => _t(str) };
}

/*
 * Setup jQuery timeago:
 * Strings in timeago are "composed" with prefixes, words and suffixes. This
 * makes their detection by our translating system impossible. Use all literal
 * strings we're using with a translation mark here so the extractor can do its
 * job.
 */
_t("less than a minute ago");
_t("about a minute ago");
_t("%d minutes ago");
_t("about an hour ago");
_t("%d hours ago");
_t("a day ago");
_t("%d days ago");
_t("about a month ago");
_t("%d months ago");
_t("about a year ago");
_t("%d years ago");

export function makeLocalization(config) {
  const langParams = Object.assign(
    {
      // Default values for localization parameters
      dateFormat: "%m/%d/%Y",
      decimalPoint: ".",
      direction: "ltr",
      grouping: [],
      multiLang: false,
      thousandsSep: ",",
      timeFormat: "%H:%M:%S",
    },
    config.langParams
  );
  Object.setPrototypeOf(translatedTerms, config.terms);
  const langDateFormat = dates.strftimeToLuxonFormat(langParams.dateFormat);
  const langTimeFormat = dates.strftimeToLuxonFormat(langParams.timeFormat);
  const langDateTimeFormat = `${langDateFormat} ${langTimeFormat}`;

  const humanNumber = (number, options = { decimals: 0, minDigits: 1 }) => {
    number = Math.round(number);
    const decimals = options.decimals || 0;
    const minDigits = options.minDigits || 1;
    const d2 = Math.pow(10, decimals);
    const numberMagnitude = +number.toExponential().split("e+")[1];
    // the case numberMagnitude >= 21 corresponds to a number
    // better expressed in the scientific format.
    if (numberMagnitude >= 21) {
      // we do not use number.toExponential(decimals) because we want to
      // avoid the possible useless O decimals: 1e.+24 preferred to 1.0e+24
      number = Math.round(number * Math.pow(10, decimals - numberMagnitude)) / d2;
      return `${number}e+${numberMagnitude}`;
    }
    const unitSymbols = _t("kMGTPE");
    const sign = Math.sign(number);
    number = Math.abs(number);
    let symbol = "";
    for (let i = unitSymbols.length; i > 0; i--) {
      const s = Math.pow(10, i * 3);
      if (s <= number / Math.pow(10, minDigits - 1)) {
        number = Math.round((number * d2) / s) / d2;
        symbol = unitSymbols[i - 1];
        break;
      }
    }
    number = sign * number;
    return (
      numbers.insertThousandsSep(number, langParams.thousandsSep, langParams.grouping) + symbol
    );
  };

  const formatDateTime = (value, options = { timezone: true }) => {
    return dates.formatDateTime(value, { format: langDateTimeFormat, timezone: options.timezone });
  };

  const formatFloat = (value, options = {}) => {
    return numbers.formatFloat(value, {
      precision: options.precision,
      decimalPoint: langParams.decimalPoint,
      thousandsSep: langParams.thousandsSep,
      grouping: langParams.grouping,
    });
  };

  const parseDate = (value, options = {}) => {
    const result = dates.parseDateTime(value, {
      format: langDateFormat,
      timezone: options.timezone,
    });
    if (result && !result.isValid) {
      throw new Error(sprintf(_t("'%s' is not a correct date"), value));
    }
    return result;
  };

  const parseDateTime = (value, options = {}) => {
    const result = dates.parseDateTime(value, {
      format: langDateTimeFormat,
      timezone: options.timezone,
    });
    if (result && !result.isValid) {
      throw new Error(sprintf(_t("'%s' is not a correct datetime"), value));
    }
    return result;
  };
  const thousandsSepRegex = new RegExp(escapeRegExp(langParams.thousandsSep), "g");
  const decimalPointRegex = new RegExp(escapeRegExp(langParams.decimalPoint), "g");
  const parseFloat = (value) => {
    const parsed = numbers.parseNumber(value, {
      thousandsSepSelector: thousandsSepRegex,
      decimalPointSelector: decimalPointRegex,
    });
    if (isNaN(parsed)) {
      throw new Error(sprintf(_t("'%s' is not a correct float"), value));
    }
    return parsed;
  };
  return {
    _t,
    ...langParams,
    formatDateTime,
    formatFloat,
    humanNumber,
    langDateFormat,
    langDateTimeFormat,
    langTimeFormat,
    parseDate,
    parseDateTime,
    parseFloat,
  };
}

export const localizationService = {
  name: "localization",
  dependencies: ["user"],
  deploy: async (env) => {
    const response = await (async function fetchLocalization() {
      const cacheHashes = odoo.session_info.cache_hashes;
      const translationsHash = cacheHashes.translations || new Date().getTime().toString();
      const lang = env.services.user.lang || null;
      let url = `/wowl/localization/${translationsHash}`;
      if (lang) {
        url += `?lang=${lang}`;
      }
      const res = await odoo.browser.fetch(url);
      if (!res.ok) {
        throw new Error("Error while fetching translations");
      }
      return res;
    })();
    const { lang_params, terms } = await response.json();
    const langParams = {
      dateFormat: lang_params && lang_params.date_format,
      decimalPoint: lang_params && lang_params.decimal_point,
      direction: lang_params && lang_params.direction,
      grouping: lang_params && lang_params.grouping,
      multiLang: lang_params && lang_params.multi_lang,
      timeFormat: lang_params && lang_params.time_format,
      thousandsSep: lang_params && lang_params.thousands_sep,
    };
    return makeLocalization({ langParams, terms });
  },
};

serviceRegistry.add("localization", localizationService);
