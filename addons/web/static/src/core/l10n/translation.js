/** @odoo-module **/

export const translatedTerms = {};

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
export function _t(term) {
    return translatedTerms[term] || term;
}

class LazyTranslatedString extends String {
    valueOf() {
        const str = super.valueOf();
        return _t(str);
    }
    toString() {
        return this.valueOf();
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
export function _lt(term) {
    return new LazyTranslatedString(term);
}

/*
 * Setup jQuery timeago:
 * Strings in timeago are "composed" with prefixes, words and suffixes. This
 * makes their detection by our translating system impossible. Use all literal
 * strings we're using with a translation mark here so the extractor can do its
 * job.
 */
_lt("less than a minute ago");
_lt("about a minute ago");
_lt("%d minutes ago");
_lt("about an hour ago");
_lt("%d hours ago");
_lt("a day ago");
_lt("%d days ago");
_lt("about a month ago");
_lt("%d months ago");
_lt("about a year ago");
_lt("%d years ago");

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
