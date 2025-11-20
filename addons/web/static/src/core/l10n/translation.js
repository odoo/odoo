import { formatList } from "@web/core/l10n/utils";
import { isIterable } from "@web/core/utils/arrays";
import { Deferred } from "@web/core/utils/concurrency";
import { htmlSprintf, isMarkup } from "@web/core/utils/html";
import { mapSubstitutions, sprintf } from "@web/core/utils/strings";

/**
 * @typedef {ReturnType<markup>} Markup
 */

/**
 * Returns true if the given value is a non-empty string, i.e. it contains other
 * characters than white spaces and zero-width spaces.
 *
 * @param {unknown} value
 */
function isNotBlank(value) {
    return typeof value === "string" && !R_BLANK.test(value);
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
        // The `!(value instanceof String)` check is to prevent interpreting `Markup` and `TranslatedString`
        // objects as iterables, since they are both subclasses of `String`.
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
 * @typedef {import("@web/core/utils/strings").Substitutions<T>} Substitutions
 */

const DEFAULT_MODULE = "base";
const R_BLANK = /^[\s\u200B]*$/;

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
 * @param {string} source
 * @param {Substitutions} substitutions
 * @returns {string | Markup | TranslatedString}
 */
export function _t(source, ...substitutions) {
    return appTranslateFn(source, odoo.translationContext, ...substitutions);
}

/**
 * This is a wrapper for _t that the transpiler injects in its place
 * to provide the knowledge of the module from which it was called.
 *
 * Providing the context of the module is useful to avoid conflicting
 * translations, e.g. "table" has a different meaning depending on the module:
 * the table of a restaurant (POS module) vs. a spreadsheet table.
 *
 * @param {string} source The term to translate
 * @param {string} moduleName The name of the module, used as a context key to
 * retrieve the translation.
 * @param  {Substitutions} substitutions The other arguments passed to _t.
 * @returns {string | Markup | TranslatedString}
 */
export function appTranslateFn(source, moduleName, ...substitutions) {
    const string = new TranslatedString(source, substitutions, moduleName);
    return string.lazy ? string : string.valueOf();
}

/**
 * Load the installed languages long names and code
 *
 * The result of the call is put in cache.
 * If any new language is installed, a full page refresh will happen,
 * so there is no need invalidate it.
 *
 * @param {import("services").ServiceFactories["orm"]} orm
 */
export async function loadLanguages(orm) {
    if (!loadLanguages.installedLanguages) {
        loadLanguages.installedLanguages = await orm.call("res.lang", "get_installed");
    }
    return loadLanguages.installedLanguages;
}

export class TranslatedString extends String {
    /** @type {string} */
    context;
    lazy = false;
    /** @type {Substitutions} */
    substitutions;

    /**
     *
     * @param {string} value
     * @param {Substitutions} substitutions
     * @param {string | null} [context]
     */
    constructor(value, substitutions, context) {
        super(value);

        if (!isNotBlank(value)) {
            return new String(value);
        }

        this.lazy = !translatedTerms[translationLoaded];
        this.substitutions = substitutions;
        this.context = context || DEFAULT_MODULE;
    }

    toString() {
        return this.valueOf();
    }

    valueOf() {
        const source = super.valueOf();
        if (this.lazy && !translatedTerms[translationLoaded]) {
            // Evaluate lazy translated string while translations are not loaded
            // -> error
            throw new Error(`Cannot translate string: translations have not been loaded`);
        }
        const translation =
            translatedTerms[this.context]?.[source] ?? translatedTermsGlobal[source] ?? source;
        if (this.substitutions.length) {
            return translationSprintf(translation, this.substitutions);
        } else {
            return translation;
        }
    }
}

export const translationLoaded = Symbol("translationLoaded");
/** @type {Record<string, string>} */
export const translatedTerms = {
    [translationLoaded]: false,
};
/**
 * Contains all the translated terms. Unlike "translatedTerms", there is no
 * "namespacing" by module. It is used as a fallback when no translation is
 * found within the module's context, or when the context is not known.
 */
export const translatedTermsGlobal = Object.create(null);
export const translationIsReady = new Deferred();
