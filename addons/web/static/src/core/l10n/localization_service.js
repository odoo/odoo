/** @odoo-module **/

import { browser } from "../browser/browser";
import { registry } from "../registry";
import { strftimeToLuxonFormat } from "./dates";
import { localization } from "./localization";
import { translatedTerms, _t } from "./translation";
import { session } from "@web/session";

export const localizationService = {
    dependencies: ["user"],
    start: async (env, { user }) => {
        // add "data-toolip" to the list of translatable attributes in owl templates
        owl.config.translatableAttributes.push("data-tooltip");

        const cacheHashes = session.cache_hashes || {};
        const translationsHash = cacheHashes.translations || new Date().getTime().toString();
        const lang = user.lang || null;
        const translationURL = session.translationURL || "/web/webclient/translations";
        let url = `${translationURL}/${translationsHash}`;
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

registry.category("services").add("localization", localizationService);
