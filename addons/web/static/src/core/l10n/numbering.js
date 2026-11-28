const { Settings } = luxon;

const LATIN_DIGITS = "0123456789";

/** @type {Map<string, string[]>} */
const digitsCache = new Map();

/**
 * @param {string} numberingSystem
 * @returns {string[]} the ten digits of the given numbering system
 */
function getDigits(numberingSystem) {
    let digits = digitsCache.get(numberingSystem);
    if (!digits) {
        // "en" is used as it is always available, contrary to some locales
        // (e.g. "bo") which would make Intl ignore the numbering system
        const formatter = new Intl.NumberFormat(`en-u-nu-${numberingSystem}`, {
            useGrouping: false,
        });
        digits = [...LATIN_DIGITS].map((digit) => formatter.format(Number(digit)));
        digitsCache.set(numberingSystem, digits);
    }
    return digits;
}

/**
 * @returns {string | undefined} the numbering system of the user language, if
 *  it isn't the latin one
 */
function getNumberingSystem() {
    // set by the localization plugin from the language parameters, and used
    // by luxon to format the dates
    const numberingSystem = Settings.defaultNumberingSystem;
    return numberingSystem && numberingSystem !== "latn" ? numberingSystem : undefined;
}

/**
 * Replaces the latin digits of the given value by the digits of the numbering
 * system of the user language (e.g. 12.5 becomes "١٢.٥" in arabic).
 *
 * This is meant for values displayed to the user: the result must not be
 * parsed back with `Number` or `parseFloat` (see `normalizeDigits`).
 *
 * @template T
 * @param {T} value a number or a string, other values are returned unchanged
 * @returns {T | string}
 */
export function localizeDigits(value) {
    const numberingSystem = getNumberingSystem();
    if (!numberingSystem || (typeof value !== "number" && typeof value !== "string")) {
        return value;
    }
    const digits = getDigits(numberingSystem);
    return String(value).replace(/[0-9]/g, (digit) => digits[digit]);
}

/**
 * Replaces the digits of the numbering system of the user language by latin
 * digits, so that a value typed by the user can be parsed.
 *
 * @param {string} value
 * @returns {string}
 */
export function normalizeDigits(value) {
    const numberingSystem = getNumberingSystem();
    if (!numberingSystem || typeof value !== "string") {
        return value;
    }
    const digits = getDigits(numberingSystem);
    return value.replace(new RegExp(`[${digits.join("")}]`, "g"), (digit) =>
        String(digits.indexOf(digit))
    );
}
