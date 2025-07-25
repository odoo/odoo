import { markup } from "@odoo/owl";

import { formatList } from "@web/core/l10n/utils";
import { isIterable } from "@web/core/utils/arrays";
import { Deferred } from "@web/core/utils/concurrency";
import { htmlSprintf } from "@web/core/utils/html";
import { isObject } from "@web/core/utils/objects";
import { sprintf } from "@web/core/utils/strings";

export const translationLoaded = Symbol("translationLoaded");
export const translatedTerms = {
    [translationLoaded]: false,
};
/**
 * Contains all the translated terms. Unlike "translatedTerms", there is no
 * "namespacing" by module. It is used as a fallback when no translation is
 * found within the module's context, or when the context is not known.
 */
export const translatedTermsGlobal = {};
export const translationIsReady = new Deferred();

const Markup = markup().constructor;

/**
 * Translates a term, or returns the term as it is if no translation can be
 * found.
 *
 * Extra positional arguments are inserted in place of %s placeholders.
 *
 * If the first extra argument is an object, the keys of that object are used to
 * map its entries to keyworded placeholders (%(kw_placeholder)s) for
 * replacement.
 *
 * If one or more of the extra arguments are iterables, they will be turned
 * into language-specific formatted strings representing the elements of the
 * list.
 *
 * If at least one of the extra arguments is a markup, the translation and
 * non-markup content are escaped, and the result is wrapped in a markup.
 *
 * @example
 * _t("Good morning"); // "Bonjour"
 * _t("Good morning %s", user.name); // "Bonjour Marc"
 * _t("Good morning %(newcomer)s, goodbye %(departer)s", { newcomer: Marc, departer: Mitchel }); // Bonjour Marc, au revoir Mitchel
 * _t("I love %s", markup`<blink>Minecraft</blink>`); // Markup {"J'adore <blink>Minecraft</blink>"}
 * _t("Good morning %s!", ["Mitchell", "Marc", "Louis"]); // Bonjour Mitchell, Marc et Louis !
 *
 * @param {string} term
 * @returns {string|Markup|LazyTranslatedString}
 */
export function _t(term, ...values) {
    if (translatedTerms[translationLoaded]) {
        const translation = _getTranslation(term, odoo.translationContext);
        if (values.length === 0) {
            return translation;
        }
        return _safeFormatAndSprintf(translation, ...values);
    } else {
        return new LazyTranslatedString(term, values);
    }
}

class LazyTranslatedString extends String {
    constructor(term, values) {
        super(term);
        this.translationContext = odoo.translationContext;
        this.values = values;
    }
    valueOf() {
        const term = super.valueOf();
        if (translatedTerms[translationLoaded]) {
            const translation = _getTranslation(term, this.translationContext);
            if (this.values.length === 0) {
                return translation;
            }
            return _safeFormatAndSprintf(translation, ...this.values);
        } else {
            throw new Error(`translation error`);
        }
    }
    toString() {
        return this.valueOf();
    }
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

/**
 * Load the installed languages long names and code
 *
 * The result of the call is put in cache.
 * If any new language is installed, a full page refresh will happen,
 * so there is no need invalidate it.
 */
export async function loadLanguages(orm) {
    if (!loadLanguages.installedLanguages) {
        loadLanguages.installedLanguages = await orm.call("res.lang", "get_installed");
    }
    return loadLanguages.installedLanguages;
}

function _getTranslation(sourceTerm, ctx) {
    return translatedTerms[ctx]?.[sourceTerm] ?? translatedTermsGlobal[sourceTerm] ?? sourceTerm;
}

/**
 * Same behavior as sprintf, but doing two additional things:
 * - If any of the provided values is an iterable, it will format its items
 *   as a language-specific formatted string representing the elements of the
 *   list.
 * - If any of the provided values is a markup, it will escape all non-markup
 *   content before performing the interpolation, then wraps the result in a
 *   markup.
 *
 * @param {string} str The string with placeholders (%s) to insert values into.
 * @param  {...any} values Primitive values to insert in place of placeholders.
 * @returns {string|Markup}
 */
function _safeFormatAndSprintf(str, ...values) {
    let hasMarkup = false;
    let valuesObject = values;
    if (values.length === 1 && isObject(values[0])) {
        valuesObject = values[0];
    }
    for (const [key, value] of Object.entries(valuesObject)) {
        // The `!(value instanceof String)` check is to prevent interpreting `Markup` and `LazyTranslatedString`
        // objects as iterables, since they are both subclasses of `String`.
        if (isIterable(value) && !(value instanceof String)) {
            valuesObject[key] = formatList(value);
        }
        hasMarkup ||= value instanceof Markup;
    }
    if (hasMarkup) {
        return htmlSprintf(str, ...values);
    }
    return sprintf(str, ...values);
}

/**
 * This is a wrapper for _t that the transpiler injects in its place
 * to provide the knowledge of the module from which it was called.
 *
 * Providing the context of the module is useful to avoid conflicting
 * translations, e.g. "table" has a different meaning depending on the module:
 * the table of a restaurant (POS module) vs. a spreadsheet table.
 *
 * @param {string} str The term to translate
 * @param {string} moduleName The name of the module, used as a context key to
 * retrieve the translation.
 * @param  {...any} args The other arguments passed to _t.
 */
export function appTranslateFn(str, moduleName, ...args) {
    odoo.translationContext = moduleName;
    const translatedTerm = _t(str, ...args);
    odoo.translationContext = null;
    return translatedTerm;
}
