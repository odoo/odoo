import { session } from "@web/session";
import { jsToPyLocale } from "@web/core/l10n/utils";
import { user } from "@web/core/user";
import { browser } from "../browser/browser";
import { registry } from "../registry";
import { strftimeToLuxonFormat } from "./dates";
import { localization } from "./localization";
import { translatedTerms, translationLoaded, translationIsReady } from "./translation";

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
        const fetchTranslate = async () => {
            if (odoo.translationsPromise) {
                return odoo.translationsPromise;
            }
            const translationsHash = new Date().getTime().toString();
            const lang = jsToPyLocale(user.lang || document.documentElement.getAttribute("lang"));
            const translationURL = session.translationURL || "/web/webclient/translations";
            let url = `${translationURL}?unique=${translationsHash}`;
            if (lang) {
                url += `&lang=${lang}`;
            }

            const response = await browser.fetch(url);
            if (!response.ok) {
                throw new Error("Error while fetching translations");
            }
            return response.json();
        };

        const storedTranslations = browser.localStorage.getItem("webclient_translations");
        // const storedTranslationsVersion = browser.localStorage.getItem(
        //     "webclient_translations_version"
        // );

        let translationData;

        // if (storedTranslations && storedTranslationsVersion === odoo.info.server_version) {
        if (storedTranslations) {
            fetchTranslate().then((res) => {
                const fetchedMenus = JSON.stringify(res);
                if (fetchedMenus !== storedTranslations) {
                    browser.localStorage.setItem("webclient_translations", fetchedMenus);
                    translationData = res;
                    // env.bus.trigger("MENUS:APP-CHANGED");
                    // TODO: here we need to update the translations ....
                    // TODO: change all the code to have getters and it should work !
                }
            });
            translationData = JSON.parse(storedTranslations);
        } else {
            translationData = await fetchTranslate();
            // browser.localStorage.setItem(
            //     "webclient_translations_version",
            //     //TODO: the first call is on the login page, we are not in the webclient, we don't have odoo.info.server_version !
            //     odoo.info.server_version
            // );
            browser.localStorage.setItem("webclient_translations", JSON.stringify(translationData));
        }

        const {
            lang_parameters: userLocalization,
            modules: modules,
            multi_lang: multiLang,
        } = await translationData;

        // FIXME We flatten the result of the python route.
        // Eventually, we want a new python route to return directly the good result.
        const terms = {};
        for (const addon of Object.keys(modules)) {
            for (const message of modules[addon].messages) {
                terms[message.id] = message.string;
            }
        }

        Object.assign(translatedTerms, terms);
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

        const dateFormat = strftimeToLuxonFormat(userLocalization.date_format);
        const timeFormat = strftimeToLuxonFormat(userLocalization.time_format);
        const shortTimeFormat = strftimeToLuxonFormat(userLocalization.short_time_format);
        const dateTimeFormat = `${dateFormat} ${timeFormat}`;
        const grouping = JSON.parse(userLocalization.grouping);

        Object.assign(localization, {
            dateFormat,
            timeFormat,
            shortTimeFormat,
            dateTimeFormat,
            decimalPoint: userLocalization.decimal_point,
            direction: userLocalization.direction,
            grouping,
            multiLang,
            thousandsSep: userLocalization.thousands_sep,
            weekStart: userLocalization.week_start,
            code: jsToPyLocale(locale),
        });
        return localization;
    },
};

registry.category("services").add("localization", localizationService);
