import { user } from "@web/core/user";

const collatorOptions = {
    numeric: true, // Compare numbers by value, i.e. "Guest 1000" comes after "Guest 9"
};
let collator;
try {
    collator = new Intl.Collator(user.lang || "en-US", collatorOptions);
} catch {
    collator = new Intl.Collator("en-US", collatorOptions);
}

/**
 * Compares two strings according to the current locale.
 *
 * This is useful as a comparison function for sorting strings intended for
 * display to the end user. Locale-sensitive sorting is important because
 * alphabetical order varies between languages (e.g., 'Z' comes between 'S' and
 * 'T' in Estonian). Additionally, it correctly handles case and accents without
 * requiring a separate normalization function.
 *
 * Contrary to the usual convention in computer science, it sorts empty strings
 * at the end. It was designed this way based on the assumption that end users
 * care less about empty values, since they convey less information. If needed,
 * this behavior can be overridden by calling `localeCompare` with the option
 * `emptyLast: false`.
 *
 * @param {string} a
 * @param {string} b
 * @param {Object} [options={}]
 * @param {boolean} [options.emptyLast=true] If true, falsy values (such as
 * empty strings, null, or undefined) will be sorted after truthy values.
 * @returns {number} A negative integer if `a` comes before `b`, a positive
 * integer if `a` comes after `b`, or 0 if they are equal.
 *
 * @example
 * const contacts = ["charles", "Elise", "Élise", "Guest 11", "Guest 9"];
 * // without localeCompare:
 * contacts.toSorted(); // ["Elise", "Guest 11", "Guest 9", "charles", "Élise"]
 * // with localeCompare:
 * contacts.toSorted(localeCompare); // ["charles", "Elise", "Élise", "Guest 9", "Guest 11"]
 */
export function localeCompare(a, b, { emptyLast = true } = {}) {
    // prevent values like undefined to be coerced to "undefined" (string)
    a ||= "";
    b ||= "";
    if (emptyLast) {
        if (a && !b) {
            return -1;
        }
        if (!a && b) {
            return 1;
        }
    }
    return collator.compare(a, b);
}
