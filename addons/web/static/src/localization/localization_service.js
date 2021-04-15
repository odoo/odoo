/** @odoo-module **/

import { browser } from "../core/browser";
import { serviceRegistry } from "../webclient/service_registry";
import { localization } from "./localization_settings";
import { translatedTerms } from "./translation";
import { strftimeToLuxonFormat } from "../utils/dates";

export const localizationService = {
  dependencies: ["user"],
  start: async (env) => {
    const cacheHashes = odoo.session_info.cache_hashes;
    const translationsHash = cacheHashes.translations || new Date().getTime().toString();
    const lang = env.services.user.lang || null;
    let url = `/web/webclient/translations/${translationsHash}`;
    if (lang) {
      url += `?lang=${lang}`;
    }

    const response = await browser.fetch(url);
    if (!response.ok) {
      throw new Error("Error while fetching translations");
    }
    const { lang_parameters: userLocalization, modules: modules } = await response.json();

    // FIXME We flatten the result of the python route.
    // Eventually, we want a new python route to return directly the good result.
    let terms = {};
    for (const addon of Object.keys(modules)) {
      for (const message of modules[addon].messages) {
        terms[message.id] = message.string;
      }
    }

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
