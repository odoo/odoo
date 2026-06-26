import { onWillDestroy, onWillStart, plugin, Plugin, useListener } from "@odoo/owl";
import { session } from "@web/session";
import { jsToPyLocale } from "@web/core/l10n/utils";
import { user } from "@web/core/user";
import { browser } from "@web/core/browser/browser";
import { services } from "@web/core/services";
import { strftimeToLuxonFormat } from "./dates";
import { localization } from "./localization";
import { rpcBus } from "@web/core/network/rpc";
import {
    translatedTerms,
    translatedTermsGlobal,
    translationLoaded,
    translationResolvers,
} from "./translation";
import { objectToUrlEncodedString } from "@web/core/utils/urls";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { registry } from "@web/core/registry";

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

// Translations live in module-global maps shared by every Owl App on the page.
// Count the live localization plugins so the reset only runs once the last app
// is destroyed, instead of every time any single app is torn down (which would
// wipe translations still used by another app, e.g. a livechat embed).
let liveLocalizationPlugins = 0;

export class LocalizationPlugin extends Plugin {
    // we need the localization plugin to start (and be ready) before the rest
    // of the code can use translated strings, so we define here a low sequence
    // number
    static sequence = 10;

    localization = localization;

    localizationDB = new IndexedDB("localization", session.registry_hash);
    translationURL = session.translationURL || "/web/webclient/translations";
    lang = jsToPyLocale(user.lang || document.documentElement.getAttribute("lang"));

    setup() {
        useListener(rpcBus, "RPC:RESPONSE", (ev) => {
            const { method, model } = ev.detail.data.params || {};
            if (
                method === "lang_install" &&
                model === "base.language.install" &&
                !ev.detail.error
            ) {
                rpcBus.trigger("CLEAR-CACHES");
            }
        });

        liveLocalizationPlugins++;
        onWillStart(() => this.load());
        onWillDestroy(() => {
            liveLocalizationPlugins--;
            if (liveLocalizationPlugins > 0 || !translatedTerms[translationLoaded]) {
                return;
            }
            for (const key in translatedTerms) {
                delete translatedTerms[key];
            }
            for (const key in translatedTermsGlobal) {
                delete translatedTermsGlobal[key];
            }
            translatedTerms[translationLoaded] = false;
        });
    }

    async load() {
        const storedTranslations = await this.localizationDB.read(
            this.translationURL,
            JSON.stringify({ lang: this.lang })
        );

        const translationProm = this.fetchTranslations(storedTranslations?.hash);
        if (storedTranslations) {
            this.updateTranslations(storedTranslations);
        } else {
            await translationProm;
        }

        translatedTerms[translationLoaded] = true;
        translationResolvers.resolve(true);

        const locale = user.lang || browser.navigator.language;
        Settings.defaultLocale = locale;
        for (const [re, numberingSystem] of NUMBERING_SYSTEMS) {
            if (re.test(locale)) {
                Settings.defaultNumberingSystem = numberingSystem;
                break;
            }
        }
        localization.locale = locale;
        localization.code = jsToPyLocale(locale);
    }

    async fetchTranslations(hash) {
        let queryString = objectToUrlEncodedString({ hash, lang: this.lang });
        queryString = queryString.length > 0 ? `?${queryString}` : queryString;
        const response = await browser.fetch(`${this.translationURL}${queryString}`, {
            cache: "no-store",
        });
        if (!response.ok) {
            throw new Error("Error while fetching translations");
        }
        const result = await response.json();
        if (result.hash !== hash) {
            this.localizationDB.write(
                this.translationURL,
                JSON.stringify({ lang: this.lang }),
                result
            );
            this.updateTranslations(result);
        }
    }

    updateTranslations(result) {
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
    }
}

services.add(LocalizationPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of localization services are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("localization", {
    start() {
        const localizationPlugin = plugin(LocalizationPlugin);
        return localizationPlugin.localization;
    },
});
