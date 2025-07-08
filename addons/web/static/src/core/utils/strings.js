import { isObject } from "./objects";

export const nbsp = "\u00a0";

/**
 * Escapes a string for HTML.
 *
 * @param {string | number} [str] the string to escape
 * @returns {string} an escaped string
 */
export function escape(str) {
    if (str === undefined) {
        return "";
    }
    if (typeof str === "number") {
        return String(str);
    }
    [
        ["&", "&amp;"],
        ["<", "&lt;"],
        [">", "&gt;"],
        ["'", "&#x27;"],
        ['"', "&quot;"],
        ["`", "&#x60;"],
    ].forEach((pairs) => {
        str = String(str).replaceAll(pairs[0], pairs[1]);
    });
    return str;
}

/**
 * Escapes a string to use as a RegExp.
 * @url https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions#Escaping
 *
 * @param {string} str
 * @returns {string} escaped string to use as a RegExp
 */
export function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
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
 * @param {string} separator
 * @returns {string}
 */
export function intersperse(str, indices, separator = "") {
    separator = separator || "";
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
        result.push(str.substring(last - section, last));
        last -= section;
    }
    const s = str.substring(0, last);
    if (s) {
        result.push(s);
    }
    return result.reverse().join(separator);
}

/**
 * Returns a string formatted using given values.
 * If the value is an object, its keys will replace `%(key)s` expressions.
 * If the values are a set of strings, they will replace `%s` expressions.
 * If no value is given, the string will not be formatted.
 *
 * @param {string} s
 * @param {any[]} values
 * @returns {string}
 */
export function sprintf(s, ...values) {
    if (values.length === 1 && isObject(values[0])) {
        const valuesDict = values[0];
        s = s.replace(/%\(([^)]+)\)s/g, (match, value) => valuesDict[value]);
    } else if (values.length > 0) {
        s = s.replace(/%s/g, () => values.shift());
    }
    return s;
}

/**
 * Capitalizes a string: "abc def" => "Abc def"
 *
 * @param {string} s the input string
 * @returns {string}
 */
export function capitalize(s) {
    return s ? s[0].toUpperCase() + s.slice(1) : "";
}

/**
 * @param {string} value
 * @returns boolean
 */
export function isEmail(value) {
    // http://stackoverflow.com/questions/46155/validate-email-address-in-javascript
    const re =
        // eslint-disable-next-line no-useless-escape
        /^(([^<>()\[\]\.,;:\s@\"]+(\.[^<>()\[\]\.,;:\s@\"]+)*)|(\".+\"))@(([^<>()[\]\.,;:\s@\"]+\.)+[^<>()[\]\.,;:\s@\"]{2,})$/i;
    return re.test(value);
}

/**
 * Return true if the string is composed of only digits
 *
 * @param {string} value
 * @returns boolean
 */

export function isNumeric(value) {
    return Boolean(value?.match(/^\d+$/));
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
    return str ? !/^false|0$/i.test(str) : trueIfEmpty;
}

/**
 * Generate a unique identifier (64 bits) in hexadecimal.
 *
 * @returns {string}
 */
export function uuid() {
    const array = new Uint8Array(8);
    window.crypto.getRandomValues(array);
    // Uint8Array to hex
    return [...array].map((b) => b.toString(16).padStart(2, "0")).join("");
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
