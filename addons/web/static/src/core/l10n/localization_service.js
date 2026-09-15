// @ts-check
/** @odoo-module native */

import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { makeLogger } from "@web/core/debug/debug_logger";
import { strftimeToLuxonFormat } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { Settings } from "@web/core/l10n/luxon";
import { jsToPyLocale, pyToJsLocale } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";
import {
    translatedTerms,
    translatedTermsGlobal,
    translationIsReady,
    translationLoaded,
} from "@web/core/translation";
import { user } from "@web/core/user";
import { l10nLog } from "@web/core/utils/asset_log";
import { IndexedDB } from "@web/core/utils/indexed_db";
import { objectToUrlEncodedString } from "@web/core/utils/urls";
import { session } from "@web/session";

/** @type {[RegExp, string][]} */
const NUMBERING_SYSTEMS = [
    [/^ar-(sa|sy|001)$/i, "arab"],
    [/^bn/i, "beng"],
    [/^bo/i, "tibt"],
    [/^pa-in/i, "guru"],
    [/^ta/i, "tamldec"],
    [/.*/i, "latn"],
];

/**
 * @param {string} locale
 * @returns {void}
 */
export function applyLuxonLocale(locale) {
    Settings.defaultLocale = locale;
    for (const [re, numberingSystem] of NUMBERING_SYSTEMS) {
        if (re.test(locale)) {
            Settings.defaultNumberingSystem = numberingSystem;
            break;
        }
    }
}

/** @returns {string} */
function getPageLocale() {
    const htmlLang = document.documentElement.getAttribute("lang");
    if (session.is_frontend) {
        return pyToJsLocale(cookie.get("frontend_lang") ?? "") || htmlLang || "en-US";
    }
    return user.lang || htmlLang || browser.navigator.language;
}

const FALLBACK_LANG_PARAMETERS = {
    date_format: "%m/%d/%Y",
    time_format: "%H:%M:%S",
    decimal_point: ".",
    direction: "ltr",
    grouping: "[3,0]",
    thousands_sep: ",",
    week_start: 7,
};

/**
 * @typedef {{
 * hash: string,
 * modules: Record<string, { messages: { id: string, string: string }[] }>,
 * lang_parameters: {
 * date_format: string,
 * time_format: string,
 * decimal_point: string,
 * direction: string,
 * grouping: string,
 * thousands_sep: string,
 * week_start: number,
 * },
 * multi_lang: boolean,
 * }} TranslationPayload
 */

/**
 * @typedef {{
 * db: IndexedDB,
 * url: string,
 * lang: string,
 * cacheMarker: string,
 * }} TranslationSource
 */

/** @param {string} cacheMarker */
function markTranslationsCached(cacheMarker) {
    try {
        browser.localStorage.setItem("webclient_translations_version", cacheMarker);
    } catch {}
}

/** @param {TranslationPayload} result */
function updateTranslations(result) {
    /** @type {Record<string, Record<string, string>>} */
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
        translationsHash: result.hash,
        dateFormat,
        timeFormat,
        dateTimeFormat: `${dateFormat} ${timeFormat}`,
        decimalPoint: userLocalization.decimal_point,
        direction: userLocalization.direction,
        grouping: (() => {
            try {
                return JSON.parse(userLocalization.grouping);
            } catch {
                return [3, 0];
            }
        })(),
        multiLang: result.multi_lang,
        thousandsSep: userLocalization.thousands_sep,
        weekStart: userLocalization.week_start,
    });
}

const log = makeLogger("web.l10n");

/**
 * @param {TranslationSource} source
 * @param {string | undefined} hash
 */
async function fetchTranslations(source, hash) {
    const { db, lang } = source;
    let queryString = objectToUrlEncodedString({ hash, lang });
    queryString = queryString.length ? `?${queryString}` : queryString;
    const url = `${source.url}${queryString}`;
    const preload = /** @type {any} */ (odoo);
    const endFetch = log.perf(`fetchTranslations ${lang}`);
    let responsePromise;
    if (
        !hash &&
        preload.loadTranslationsPromise &&
        preload.loadTranslationsURL === url
    ) {
        l10nLog("fetch", "fetchTranslations adopting preload", `url=${url}`);
        responsePromise = preload.loadTranslationsPromise;
    } else {
        if (preload.loadTranslationsPromise) {
            preload.loadTranslationsPromise.then(
                (/** @type {Response} */ res) => res.body?.cancel(),
                () => {},
            );
        }
        l10nLog("fetch", "fetchTranslations begin", `url=${url}`);
        responsePromise = browser.fetch(url, { cache: "no-store" });
    }
    preload.loadTranslationsPromise = null;
    preload.loadTranslationsURL = null;
    const response = await responsePromise;
    l10nLog(
        "fetch",
        "fetchTranslations response",
        `status=${response.status}`,
        `ok=${response.ok}`,
    );
    if (!response.ok) {
        endFetch({ status: response.status });
        throw new Error("Error while fetching translations");
    }
    const result = await response.json();
    endFetch({
        status: response.status,
        hash: Boolean(hash),
        modules: Object.keys(result.modules || {}).length,
    });
    if (result.hash !== hash) {
        updateTranslations(result);
        db.write(source.url, JSON.stringify({ lang }), result).then(
            () => markTranslationsCached(source.cacheMarker),
            () => {},
        );
        l10nLog("fetch", "fetchTranslations cached + applied", `hash=${result.hash}`);
    }
}

const localizationService = {
    /** @returns {Promise<typeof import("@web/core/l10n/localization").localization>} */
    start: async () => {
        const locale = getPageLocale();
        const lang = jsToPyLocale(locale);
        /** @type {TranslationSource} */
        const source = {
            db: new IndexedDB("localization", session.registry_hash),
            url: session.translationURL || "/web/webclient/translations",
            lang,
            cacheMarker: `${session.registry_hash}/${lang}`,
        };

        const storedTranslations = await source.db.read(
            source.url,
            JSON.stringify({ lang }),
        );
        l10nLog(
            "cache",
            "storedTranslations",
            `hit=${Boolean(storedTranslations)}`,
            `hash=${storedTranslations?.hash}`,
            `lang=${lang}`,
        );

        const translationProm = fetchTranslations(source, storedTranslations?.hash);
        if (storedTranslations) {
            translationProm.catch((e) =>
                console.warn("Background translation fetch failed:", e),
            );
            markTranslationsCached(source.cacheMarker);
            updateTranslations(storedTranslations);
        } else {
            l10nLog("cache", "no cache, awaiting fetch");
            try {
                await translationProm;
            } catch (e) {
                console.error(
                    "Translation fetch failed on cold boot; falling back to default localization parameters:",
                    e,
                );
                updateTranslations({
                    hash: "",
                    modules: {},
                    lang_parameters: FALLBACK_LANG_PARAMETERS,
                    multi_lang: false,
                });
            }
        }

        translatedTerms[translationLoaded] = true;
        translationIsReady.resolve(true);

        applyLuxonLocale(locale);
        localization.code = lang;
        return localization;
    },
};

registry.category("services").add("localization", localizationService);
