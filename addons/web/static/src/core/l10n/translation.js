/** @odoo-module **/

import { Deferred } from "@web/core/utils/concurrency";
export const translationLoaded = Symbol("translationLoaded");
export const translatedTerms = {
    [translationLoaded]: false,
};
export const translationIsReady = new Deferred();
/**
 * Translate a term, or return the term if no translation can be found.
 *
 * @param {string} term
 * @returns {string}
 */
export function _t(term) {
    if (translatedTerms[translationLoaded]) {
        return translatedTerms[term] || term;
    } else {
        return new LazyTranslatedString(term);
    }
}

class LazyTranslatedString extends String {
    valueOf() {
        const term = super.valueOf();
        if (translatedTerms[translationLoaded]) {
            return translatedTerms[term] || term;
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
