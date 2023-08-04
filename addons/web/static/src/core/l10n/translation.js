/** @odoo-module **/

import { Deferred } from "@web/core/utils/concurrency";
import { sprintf } from "@web/core/utils/strings";

export const translationLoaded = Symbol("translationLoaded");
export const translatedTerms = {
    [translationLoaded]: false,
};
export const translationIsReady = new Deferred();
/**
 * Translate a term, or return the term if no translation can be found.
 *
 * Note that it translates eagerly, which means that if the translations have
 * not been loaded yet, it will return the untranslated term. If it cannot be
 * guaranteed that translations are ready, one should use the _lt function
 * instead (see below)
 *
 * @param {string} term
 * @returns {string}
 */
export function _t(term, ...values) {
    if (translatedTerms[translationLoaded]) {
        const translation = translatedTerms[term] ?? term;
        if (values.length === 0) {
            return translation;
        }
        return sprintf(translation, ...values);
    } else {
        return new LazyTranslatedString(term, ...values);
    }
}

/**
 * Lazy translation function, only performs the translation when actually
 * printed (e.g. inserted into a template).
 * Useful when defining translatable strings in code evaluated before the
 * translations are loaded, as class attributes or at the top-level of
 * an Odoo Web module
 *
 * @param {string} term
 * @returns {LazyTranslatedString}
 */
export const _lt = (term, ...values) => _t(term, ...values);

class LazyTranslatedString extends String {
    constructor(term, ...values) {
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
            return sprintf(translation, ...this.values);
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
