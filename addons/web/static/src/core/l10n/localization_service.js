import { session } from "@web/session";
import { jsToPyLocale } from "@web/core/l10n/utils";
import { user } from "@web/core/user";
import { browser } from "../browser/browser";
import { registry } from "../registry";
import { strftimeToLuxonFormat } from "./dates";
import { localization } from "./localization";
import {
    translatedTerms,
    translatedTermsGlobal,
    translationLoaded,
    translationIsReady,
} from "./translation";
import { objectToUrlEncodedString } from "../utils/urls";
import { IndexedDB } from "../utils/indexed_db";

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

export const localizationService = {
    start: async () => {
        const localizationDB = new IndexedDB("localization", session.registry_hash);
        const translationURL = session.translationURL || "/web/webclient/translations";
        const lang = jsToPyLocale(user.lang || document.documentElement.getAttribute("lang"));

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
            JSON.stringify({ lang })
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
