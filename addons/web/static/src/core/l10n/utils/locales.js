/**
 * Converts a locale from JavaScript to Python format.
 *
 * Most of the time the conversion is simply to replace - with _.
 * Example: fr-BE → fr_BE
 *
 * Exceptions:
 *  - Serbian can be written in both Latin and Cyrillic scripts interchangeably,
 *  therefore its locale includes a special modifier to indicate which script to
 *  use. Example: sr-Latn → sr@latin
 *  - Tagalog/Filipino: The "fil" locale is replaced by "tl" for compatibility
 *  with the Python side (where the "fil" locale doesn't exist).
 *
 * BCP 47 (JS):
 *  language[-extlang][-script][-region][-variant][-extension][-privateuse]
 *  https://www.ietf.org/rfc/rfc5646.txt
 * XPG syntax (Python):
 *  language[_territory][.codeset][@modifier]
 *  https://www.gnu.org/software/libc/manual/html_node/Locale-Names.html
 *
 * @param {string} locale The locale formatted for use on the JavaScript-side.
 * @returns {string} The locale formatted for use on the Python-side.
 */
export function jsToPyLocale(locale) {
    if (!locale) {
        return "";
    }
    try {
        var { language, script, region } = new Intl.Locale(locale);
        // new Intl.Locale("tl-PH") produces fil-PH, which one might not expect
        if (language === "fil") {
            language = "tl";
        }
    } catch {
        return locale;
    }
    let xpgLocale = language;
    if (region) {
        xpgLocale += `_${region}`;
    }
    switch (script) {
        case "Cyrl":
            xpgLocale += "@Cyrl";
            break;
        case "Latn":
            xpgLocale += "@latin";
            break;
    }
    return xpgLocale;
}

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
 *  https://www.ietf.org/rfc/rfc5646.txt
 * XPG syntax (Python):
 *  language[_territory][.codeset][@modifier]
 *  https://www.gnu.org/software/libc/manual/html_node/Locale-Names.html
 *
 * @param {string} locale The locale formatted for use on the Python-side.
 * @returns {string} The locale formatted for use on the JavaScript-side.
 */
export function pyToJsLocale(locale) {
    if (!locale) {
        return "";
    }
    const regex = /^([a-z]+)(_[A-Z\d]+)?(@.+)?$/;
    const match = locale.match(regex);
    if (!match) {
        return locale;
    }
    const [, language, territory, modifier] = match;
    const subtags = [language];
    switch (modifier) {
        case "@Cyrl":
            subtags.push("Cyrl");
            break;
        case "@latin":
            subtags.push("Latn");
            break;
    }
    if (territory) {
        subtags.push(territory.slice(1));
    }
    return subtags.join("-");
}
