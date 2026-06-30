import { isObject } from "./objects";

/**
 * @template [T=unknown]
 * @typedef {[Record<string, T>] | T[]} Substitutions
 */

/**
 * @param {Substitutions} substitutions
 */
function hasSubstitutionDict(substitutions) {
    return substitutions.length === 1 && isObject(substitutions[0]);
}

const HTML_ESCAPED_CHARACTERS = [
    ["&", "&amp;"],
    ["<", "&lt;"],
    [">", "&gt;"],
    ["'", "&#x27;"],
    ['"', "&quot;"],
    ["`", "&#x60;"],
];

/**
 * Based on:
 * {@link http://stackoverflow.com/questions/46155/validate-email-address-in-javascript}
 */
const R_EMAIL =
    /^(([^<>()[\].,;:\s@"]+(\.[^<>()[\].,;:\s@"]+)*)|(".+"))@(([^<>()[\].,;:\s@"]+\.)+[^<>()[\].,;:\s@"]{2,})$/i;
const R_FALSY = /^false|0$/i;
const R_KEYED_SUBSTITUTION = /%\((?<key>[^)]+)\)s/g;
const R_NUMERIC = /^\d+$/;
const R_REGEX_SPECIAL_CHARS = /[.*+?^${}()|[\]\\]/g;

export const nbsp = "\u00a0";

/**
 * Capitalizes a string: "abc def" => "Abc def"
 *
 * @param {string} str the input string
 * @returns {string}
 */
export function capitalize(str) {
    return str ? str[0].toUpperCase() + str.slice(1) : "";
}

/**
 * Escapes HTML special characters in a given value.
 *
 * @param {unknown} [value]
 * @returns {string}
 */
export function escape(value) {
    if (typeof value !== "string") {
        return String(value ?? "");
    }
    for (const [char, replacer] of HTML_ESCAPED_CHARACTERS) {
        value = value.replaceAll(char, replacer);
    }
    return value;
}

/**
 * Escapes a pattern to use as a RegExp.
 *
 * {@link https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_expressions#escaping}
 *
 * @param {string} pattern
 * @returns {string} escaped string to use as a RegExp
 */
export function escapeRegExp(pattern) {
    return pattern.replaceAll(R_REGEX_SPECIAL_CHARS, "\\$&");
}

/**
 * Parse the string to check if the value is true or false
 * If the string is empty, 0, False or false it's considered as false
 * The rest is considered as true
 *
 * @param {string} str
 * @param {boolean} [trueIfEmpty=false]
 * @returns {boolean}
 */
export function exprToBoolean(str, trueIfEmpty = false) {
    return str ? !R_FALSY.test(str) : trueIfEmpty;
}

/**
 * Generate a hash, also known as a 'digest', for the given string.
 * This algorithm is based on the Java hashString method
 * (see: https://docs.oracle.com/javase/7/docs/api/java/lang/String.html#hashCode()).
 * Please note that this hash function is non-cryptographic and does not exhibit collision resistance.
 *
 * If a cryptographic hash function is required, the digest() function of the SubtleCrypto
 * interface makes various hash functions available:
 * https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest
 *
 * @param {string} str
 * @returns {string}
 */
export function hashCode(...strings) {
    const str = strings.join("\x1C");

    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = (hash << 5) - hash + str.charCodeAt(i);
        hash |= 0;
    }

    // Convert the possibly negative number hash code into an 8 character
    // hexadecimal string
    return (hash + 16 ** 8).toString(16).slice(-8);
}

/**
 * Intersperses ``separator`` in ``str`` at the positions indicated by
 * ``indices``.
 *
 * ``indices`` is an array of relative offsets (from the previous insertion
 * position, starting from the end of the string) at which to insert
 * ``separator``.
 *
 * There are two special values:
 *
 * ``-1``
 *   indicates the insertion should end now
 * ``0``
 *   indicates that the previous section pattern should be repeated (until all
 *   of ``str`` is consumed)
 *
 * @param {string} str
 * @param {number[]} indices
 * @param {string} [separator=""]
 * @returns {string}
 */
export function intersperse(str, indices, separator) {
    /** @type {string[]} */
    const result = [];
    let last = str.length;
    for (let i = 0; i < indices.length; ++i) {
        let section = indices[i];
        if (section === -1 || last <= 0) {
            // Done with string, or -1 (stops formatting string)
            break;
        } else if (section === 0 && i === 0) {
            // repeats previous section, which there is none => stop
            break;
        } else if (section === 0) {
            // repeat previous section forever
            //noinspection AssignmentToForLoopParameterJS
            section = indices[--i];
        }
        result.unshift(str.substring(last - section, last));
        last -= section;
    }
    const substr = str.substring(0, last);
    if (substr) {
        result.unshift(substr);
    }
    return result.join(separator || "");
}

/**
 * @param {string} value
 * @returns {boolean}
 */
export function isEmail(value) {
    return R_EMAIL.test(value);
}

/**
 * Return true if the string is composed of only digits
 *
 * @param {string} value
 * @returns {boolean}
 */
export function isNumeric(value) {
    return R_NUMERIC.test(value);
}

/**
 * @template T, M
 * @param {Substitutions<T>} substitutions
 * @param {(value: T) => M} mapFn
 * @returns {Substitutions<M>}
 */
export function mapSubstitutions(substitutions, mapFn) {
    if (hasSubstitutionDict(substitutions)) {
        const substitutionDict = {};
        for (const [key, value] of Object.entries(substitutions[0])) {
            substitutionDict[key] = mapFn(value);
        }
        return [substitutionDict];
    } else {
        return substitutions.map(mapFn);
    }
}

/**
 * Returns a string formatted using given values.
 *
 * If the value is an object:
 *  - its keys will replace `%(key)s` expressions;
 *  - these expressions CANNOT be escaped (e.g. '%%(key)s');
 *  - missing keys will yield empty strings.
 *
 * If the value(s) is a list of string(s):
 *  - they will replace `%s` expressions;
 *  - these expressions CAN be escaped by adding another '%';
 *  - surplus of "%s" expressions will be replaced by empty strings.
 *
 * If no value is given, the string will not be formatted at all.
 *
 * @template T
 * @param {string} str
 * @param {Substitutions<T>} substitutions
 * @returns {string}
 * @example
 *  // Generic substitutions
 *  sprintf("Hello %s!", "world"); // "Hello world!"
 *  sprintf("Hello %%s!", "world"); // "Hello %s!"
 *  // Keyed substitutions
 *  sprintf("Hello %(place)s!", { place: "world" }); // "Hello world!"
 *  sprintf("Hello %(missing)s!", { place: "world" }); // "Hello !"
 *  sprintf("Hello %%(place)s!", { place: "world" }); // "Hello %world!"
 *  // Unchanged because no substitutions
 *  sprintf("Hello %s!"); // "Hello %s!"
 */
export function sprintf(str, ...substitutions) {
    if (!substitutions.length) {
        // No substitutions => leave the string as is
        return str;
    }
    if (hasSubstitutionDict(substitutions)) {
        // Keyed (%(key)s) substitutions
        const dict = substitutions[0];
        return str.replaceAll(R_KEYED_SUBSTITUTION, (_match, key) => dict[key] ?? "");
    } else {
        // Generic (%s) substitutions
        const raw = [""];
        for (let i = 0; i < str.length; i++) {
            if (str[i] === "%") {
                if (str[i + 1] === "%") {
                    // Escaped "%" character: => single "%"
                    raw[raw.length - 1] += str[++i];
                    continue;
                }
                if (str[i + 1] === "s") {
                    // Substitution (ignore "%s" in final string)
                    i++;
                    raw.push("");
                    continue;
                }
            }
            raw[raw.length - 1] += str[i];
        }
        return String.raw({ raw }, ...substitutions);
    }
}

/**
 * Generate a unique identifier (64 bits) in hexadecimal.
 *
 * @returns {string}
 */
export function uuid() {
    let id = "";
    for (const b of crypto.getRandomValues(new Uint8Array(8))) {
        id += b.toString(16).padStart(2, "0");
    }
    return id;
}
