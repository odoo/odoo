/** @odoo-module **/

export const translatedTerms = {};

/**
 * Lazy translation function, only performs the translation when actually
 * printed (e.g. inserted into a template).
 * Useful when defining translatable strings in code evaluated before the
 * translations are loaded, as class attributes or at the top-level of
 * an Odoo Web module
 *
 * @returns {string}
 */
export function _lt(str) {
  return { toString: () => translatedTerms[str] || str };
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
