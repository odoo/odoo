// @ts-check

/** @module @web/services/localization_service - Fetches translations and configures Luxon locale, numbering system, and date/number formats */

import { browser } from "@web/core/browser/browser";
import { strftimeToLuxonFormat } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import {
    translatedTerms,
    translatedTermsGlobal,
    translationIsReady,
    translationLoaded,
} from "@web/core/l10n/translation";
import { jsToPyLocale } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { objectToUrlEncodedString } from "@web/core/utils/urls";
import { user } from "@web/services/user";
import { session } from "@web/session";

const { Settings } = luxon;

/** @type {[RegExp, string][]} */
const NUMBERING_SYSTEMS = [
    [/^ar-(sa|sy|001)$/i, "arab"],
    [/^bn/i, "beng"],
    [/^bo/i, "tibt"],
    // [/^fa/i, "Farsi (Persian)"], // No numberingSystem found in Intl
    // [/^(hi|mr|ne)/i, "Hindi"], // No numberingSystem found in Intl
    // [/^my/i, "Burmese"], // No numberingSystem found in Intl
    [/^pa-in/i, "guru"],
    [/^ta/i, "tamldec"],
    [/.*/i, "latn"],
];

/**
 * Service that fetches translations from the server and configures the Luxon
 * locale, numbering system, and Odoo localization settings (date/time formats,
 * decimal point, thousands separator, etc.).
 *
 * Uses IndexedDB for caching translations across page loads.
 */
export const localizationService = {
    /** @returns {Promise<typeof import("@web/core/l10n/localization").localization>} */
    start: async () => {
        const localizationDB = new IndexedDB("localization", session.registry_hash);
        const translationURL = session.translationURL || "/web/webclient/translations";
        const lang = jsToPyLocale(
            user.lang || document.documentElement.getAttribute("lang"),
        );

        /**
         * Fetch translations from the server. If the hash matches the cached
         * version, no update is performed.
         * @param {string | undefined} hash - hash of the currently cached translations
         */
        const fetchTranslations = async (hash) => {
            let queryString = objectToUrlEncodedString({ hash, lang });
            queryString = queryString.length > 0 ? `?${queryString}` : queryString;
            const response = await browser.fetch(`${translationURL}${queryString}`, {
                cache: "no-store",
            });
            if (!response.ok) {
                throw new Error("Error while fetching translations");
            }
            const result = await response.json();
            if (result.hash !== hash) {
                localizationDB.write(translationURL, JSON.stringify({ lang }), result);
                updateTranslations(result);
            }
        };

        /**
         * Apply translation data to the global `translatedTerms` and configure
         * the `localization` object with date/time formats and number settings.
         * @param {{ hash: string, modules: Object, lang_parameters: Object, multi_lang: boolean }} result
         */
        const updateTranslations = (result) => {
            // Eventually, we want a new python route to return directly the good result.
            const terms = {};
            for (const addon of Object.keys(result.modules)) {
                terms[addon] = {};
                for (const message of result.modules[addon].messages) {
                    terms[addon][message.id] = message.string;
                    translatedTermsGlobal[message.id] = message.string;
                }
            }
            Object.assign(translatedTerms, terms);

            const userLocalization = result.lang_parameters;
            const dateFormat = strftimeToLuxonFormat(userLocalization.date_format);
            const timeFormat = strftimeToLuxonFormat(userLocalization.time_format);

            Object.assign(localization, {
                dateFormat,
                timeFormat,
                dateTimeFormat: `${dateFormat} ${timeFormat}`,
                decimalPoint: userLocalization.decimal_point,
                direction: userLocalization.direction,
                grouping: JSON.parse(userLocalization.grouping),
                multiLang: result.multi_lang,
                thousandsSep: userLocalization.thousands_sep,
                weekStart: userLocalization.week_start,
            });
        };

        const storedTranslations = await localizationDB.read(
            translationURL,
            JSON.stringify({ lang }),
        );

        const translationProm = fetchTranslations(storedTranslations?.hash);
        if (storedTranslations) {
            updateTranslations(storedTranslations);
        } else {
            await translationProm;
        }

        translatedTerms[translationLoaded] = true;
        translationIsReady.resolve(true);

        const locale = user.lang || browser.navigator.language;
        Settings.defaultLocale = locale;
        for (const [re, numberingSystem] of NUMBERING_SYSTEMS) {
            if (re.test(locale)) {
                Settings.defaultNumberingSystem = numberingSystem;
                break;
            }
        }
        localization.code = jsToPyLocale(locale);
        return localization;
    },
};

registry.category("services").add("localization", localizationService);
