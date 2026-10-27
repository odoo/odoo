/** @odoo-module **/

/**
 * Converts a locale from Python to JavaScript format.
 *
 * Most of the time the conversion is simply to replace _ with -.
 * Example: fr_BE → fr-BE
 *
 * Exception: Serbian can be written in both Latin and Cyrillic scripts
 * interchangeably, therefore its locale includes a special modifier
 * to indicate which script to use.
 * Example: sr@latin → sr-Latn
 *
 * BCP 47 (JS):
 *  language[-extlang][-script][-region][-variant][-extension][-privateuse]
 * XPG syntax (Python):
 *  language[_territory][.codeset][@modifier]
 *
 * @param {string} locale The locale formatted for use on the Python-side.
 * @returns {string} The locale formatted for use on the JavaScript-side.
 */
export function pyToJsLocale(locale) {
    if (!locale) {
        return "";
    }
    const match = locale.match(/^([a-z]+)(_[A-Z\d]+)?(@.+)?$/);
    if (!match) {
        return locale;
    }
    const [, language, territory, modifier] = match;
    const subtags = [language];
    if (modifier === "@latin") {
        subtags.push("Latn");
    }
    if (territory) {
        subtags.push(territory.slice(1));
    }
    return subtags.join("-");
}
