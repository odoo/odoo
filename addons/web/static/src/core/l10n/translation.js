import { markup } from "@odoo/owl";

import { Deferred } from "@web/core/utils/concurrency";
import { escape, sprintf } from "@web/core/utils/strings";

export const translationLoaded = Symbol("translationLoaded");
export const translatedTerms = {
    [translationLoaded]: false,
};
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
 * If at least one of the extra arguments is a markup, the translation and
 * non-markup content are escaped, and the result is wrapped in a markup.
 *
 * @example
 * _t("Good morning"); // "Bonjour"
 * _t("Good morning %s", user.name); // "Bonjour Marc"
 * _t("Good morning %(newcomer)s, goodbye %(departer)s", { newcomer: Marc, departer: Mitchel }); // Bonjour Marc, au revoir Mitchel
 * _t("I love %s", markup("<blink>Minecraft</blink>")); // Markup {"J'adore <blink>Minecraft</blink>"}
 *
 * @param {string} term
 * @returns {string|Markup|LazyTranslatedString}
 */
export function _t(term, ...values) {
    if (translatedTerms[translationLoaded]) {
        const translation = translatedTerms[term] ?? term;
        if (values.length === 0) {
            return translation;
        }
        return _safeSprintf(translation, ...values);
    } else {
        return new LazyTranslatedString(term, values);
    }
}

class LazyTranslatedString extends String {
    constructor(term, values) {
        super(term);
        this.values = values;
    }
    valueOf() {
        const term = super.valueOf();
        if (translatedTerms[translationLoaded]) {
            const translation = translatedTerms[term] ?? term;
            if (this.values.length === 0) {
                return translation;
            }
            return _safeSprintf(translation, ...this.values);
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

/**
 * Same behavior as sprintf, but if any of the provided values is a markup,
 * escapes all non-markup content before performing the interpolation, then
 * wraps the result in a markup.
 *
 * @param {string} str The string with placeholders (%s) to insert values into.
 * @param  {...any} values Primitive values to insert in place of placeholders.
 * @returns {string|Markup}
 */
function _safeSprintf(str, ...values) {
    let hasMarkup;
    if (values.length === 1 && Object.prototype.toString.call(values[0]) === "[object Object]") {
        hasMarkup = Object.values(values[0]).some((v) => v instanceof Markup);
    } else {
        hasMarkup = values.some((v) => v instanceof Markup);
    }
    if (hasMarkup) {
        return markup(sprintf(escape(str), ..._escapeNonMarkup(values)));
    }
    return sprintf(str, ...values);
}

/**
 * Go through each value to be passed to sprintf and escape anything that isn't
 * a markup.
 *
 * @param {any[]|[Object]} values Values for use with sprintf.
 * @returns {any[]|[Object]}
 */
function _escapeNonMarkup(values) {
    if (Object.prototype.toString.call(values[0]) === "[object Object]") {
        const sanitized = {};
        for (const [key, value] of Object.entries(values[0])) {
            sanitized[key] = value instanceof Markup ? value : escape(value);
        }
        return [sanitized];
    }
    return values.map((x) => (x instanceof Markup ? x : escape(x)));
}
