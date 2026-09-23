// @ts-check
/** @odoo-module native */

import { makeLogger } from "@web/core/debug/debug_logger";
import { localization } from "@web/core/l10n/localization";
import { formatList, pyToJsLocale } from "@web/core/l10n/utils";
import { isIterable } from "@web/core/utils/collections/arrays";
import { Deferred } from "@web/core/utils/concurrency";
import { htmlSprintf, isMarkup } from "@web/core/utils/dom/html";
import { mapSubstitutions, sprintf } from "@web/core/utils/format/strings";
import { globalSingleton } from "@web/core/utils/global_singleton";

/** @typedef {any} Markup */

const log = makeLogger("web.translation");

/**
 * @param {unknown} value
 * @returns {boolean}
 */
function isNotBlank(value) {
    return typeof value === "string" && !R_BLANK.test(value);
}

/**
 * @param {string} str
 * @param {Substitutions} substitutions
 * @returns {string | Markup | TranslatedString}
 */
function translationSprintf(str, substitutions) {
    let hasMarkup = false;

    /**
     * @param {string | Markup} value
     * @returns {string | Markup}
     */
    function formatSubstitution(value) {
        hasMarkup ||= isMarkup(value);
        if (isIterable(value) && !(value instanceof String)) {
            return formatList(value);
        } else {
            return value;
        }
    }
    const formattedSubstitutions = mapSubstitutions(substitutions, formatSubstitution);
    if (hasMarkup) {
        return htmlSprintf(str, ...formattedSubstitutions);
    } else {
        return sprintf(str, ...formattedSubstitutions);
    }
}

/**
 * @template [T=unknown]
 * @typedef {import("@web/core/utils/format/strings").Substitutions<T>} Substitutions
 */

const DEFAULT_MODULE = "base";
const R_BLANK = /^[\s\u200B]*$/;

/**
 * @param {string} source
 * @param {Substitutions} substitutions
 * @returns {string | Markup | TranslatedString}
 */
export function _t(source, ...substitutions) {
    return appTranslateFn(source, odoo.translationContext, ...substitutions);
}

/** @type {Map<string, Intl.PluralRules>} */
const _pluralRulesCache = new Map();

/**
 * @template {string | TranslatedString | Markup} T
 * @param {number} count
 * @param {Partial<Record<Intl.LDMLPluralRule, T>> & { other: T }} forms
 * @returns {T}
 */
export function _pl(count, forms) {
    const code = pyToJsLocale(localization.code) || "en";
    let rules = _pluralRulesCache.get(code);
    if (!rules) {
        rules = new Intl.PluralRules(code);
        _pluralRulesCache.set(code, rules);
    }
    const category = rules.select(count);
    return forms[category] ?? forms.other;
}

/**
 * @param {string} source
 * @param {string} [moduleName]
 * @param {Substitutions} substitutions
 * @returns {string | Markup | TranslatedString}
 */
export function appTranslateFn(source, moduleName, ...substitutions) {
    if (!isNotBlank(source)) {
        log.logic("untranslatable source", () => ({
            type: isMarkup(source) ? "markup" : typeof source,
            source: String(source).slice(0, 80),
            moduleName,
        }));
        return String(source);
    }
    if (translatedTerms[translationLoaded]) {
        const context = moduleName || DEFAULT_MODULE;
        const translation =
            translatedTerms[context]?.[source] ??
            translatedTermsGlobal[source] ??
            source;
        return substitutions.length
            ? translationSprintf(translation, substitutions)
            : translation;
    }
    const string = new TranslatedString(source, substitutions, moduleName);
    return string.lazy ? string : string.translate();
}

/** @param {import("services").ServiceFactories["orm"]} orm */
export async function loadLanguages(orm) {
    if (!loadLanguages.installedLanguages) {
        loadLanguages.installedLanguages = await orm.call("res.lang", "get_installed");
    }
    return loadLanguages.installedLanguages;
}
/** @type {any[] | null} */
loadLanguages.installedLanguages = null;

export class TranslatedString extends String {
    /** @type {string} */
    context;
    lazy = false;
    /** @type {Substitutions} */
    substitutions;

    /**
     * @param {string} value
     * @param {Substitutions} substitutions
     * @param {string | null} [context]
     */
    constructor(value, substitutions, context) {
        super(value);

        if (!isNotBlank(value)) {
            // @ts-expect-error — valid JS: constructor returning plain String to skip translation
            return new String(value);
        }

        this.lazy = !translatedTerms[translationLoaded];
        this.substitutions = substitutions;
        this.context = context || DEFAULT_MODULE;
    }

    /** @returns {string | Markup} */
    translate() {
        const source = super.valueOf();
        if (this.lazy && !translatedTerms[translationLoaded]) {
            throw new Error(
                `Cannot translate string: translations have not been loaded`,
            );
        }
        const translation =
            translatedTerms[this.context]?.[source] ??
            translatedTermsGlobal[source] ??
            source;
        if (this.substitutions.length) {
            return translationSprintf(translation, this.substitutions);
        } else {
            return translation;
        }
    }

    /** @returns {string} */
    toString() {
        return this.valueOf();
    }

    /** @returns {string} */
    toJSON() {
        return this.valueOf();
    }

    /** @returns {string} */
    valueOf() {
        return String(this.translate());
    }
}

/** @type {symbol} */
export const translationLoaded = Symbol.for("@web/core/l10n/translationLoaded");

/** @type {{ translatedTerms: Record<string | symbol, any>, translatedTermsGlobal: Record<string, string>, translationIsReady: Deferred }} */
const _state = globalSingleton("l10n", () => ({
    translatedTerms: { [translationLoaded]: false },
    translatedTermsGlobal: Object.create(null),
    translationIsReady: new Deferred(),
}));

/** @type {Record<string | symbol, any>} */
export const translatedTerms = _state.translatedTerms;
/** @type {Record<string, string>} */
export const translatedTermsGlobal = _state.translatedTermsGlobal;
/** @type {Deferred} */
export const translationIsReady = _state.translationIsReady;
