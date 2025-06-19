import { isObject } from "./objects";
import { markup } from "@odoo/owl";

const ESCAPE_CHARS_MAP = [
    ["&", "&amp;"],
    ["<", "&lt;"],
    [">", "&gt;"],
    ["'", "&#x27;"],
    ['"', "&quot;"],
    ["`", "&#x60;"],
];

// OdooMark regular expressions
const R_LINE_BREAK = /\n/g;
const R_TAB = /\t/g;
const R_TAG = /&#x60;(.+?)&#x60;/g;
const R_TEXT_BOLD = /\*\*(.+?)\*\*/g;
const R_TEXT_MUTED = /--(.+?)--/g;

// Other regular expressions
// http://stackoverflow.com/questions/46155/validate-email-address-in-javascript
const R_EMAIL =
    /^(([^<>()[\].,;:\s@"]+(\.[^<>()[\].,;:\s@"]+)*)|(".+"))@(([^<>()[\].,;:\s@"]+\.)+[^<>()[\].,;:\s@"]{2,})$/i;
const R_FALSY = /^false|0$/i;
const R_NUMERIC = /^\d+$/;
const R_REGEX_SPECIAL_CHAR = /[.*+?^${}()|[\]\\]/g;
const R_SPRINTF = /%s/g;
const R_SPRINTF_DICT = /%\(([^)]+)\)s/g;

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
    str = String(str);
    for (const [char, escapedChar] of ESCAPE_CHARS_MAP) {
        str = str.replaceAll(char, escapedChar);
    }
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
    return str.replaceAll(R_REGEX_SPECIAL_CHAR, "\\$&");
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
 * @param {string} [separator]
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
 * @param {string} str
 * @param {...unknown} values
 * @returns {string}
 */
export function sprintf(str, ...values) {
    if (values.length === 1 && isObject(values[0])) {
        const valuesDict = values[0];
        str = str.replaceAll(R_SPRINTF_DICT, (_match, value) => valuesDict[value]);
    } else if (values.length > 0) {
        str = str.replaceAll(R_SPRINTF, () => values.shift());
    }
    return str;
}

/**
 * Capitalizes a string: "abc def" => "Abc def"
 *
 * @param {string} str
 * @returns {string}
 */
export function capitalize(str) {
    return str ? str[0].toUpperCase() + str.slice(1) : "";
}

/**
 * Format the text as follow:
 *      \*\*text\*\* => Put the text in bold.
 *      --text-- => Put the text in muted.
 *      \`text\` => Put the text in a rounded badge (bg-primary).
 *      \n => Insert a breakline.
 *      \t => Insert 4 spaces.
 *
 * @param {string} text **will be escaped**
 * @returns {ReturnType<markup>} the formatted text
 */
export function odoomark(text) {
    return markup(
        escape(text)
            .replaceAll(R_TEXT_BOLD, `<b>$1</b>`)
            .replaceAll(R_TEXT_MUTED, `<span class='text-muted'>$1</span>`)
            .replaceAll(
                R_TAG,
                `<span class="o_tag position-relative d-inline-flex align-items-center mw-100 o_badge badge rounded-pill lh-1 o_tag_color_0">$1</span>`
            )
            .replaceAll(R_LINE_BREAK, `<br/>`)
            .replaceAll(R_TAB, `<span style="margin-left: 2em"></span>`)
    );
}

/**
 * Returns a markuped version of the input text where
 * the query is highlighted using the input classes and
 * a b tag if it is part of the text
 *
 * @param {string} query
 * @param {string} text
 * @param {string} classes
 * @returns {string}
 */
export function highlightText(query, text, classes) {
    if (!query) {
        return odoomark(text);
    }
    const regex = new RegExp(`(${escapeRegExp(escape(query))})+(?=(?:[^>]*<[^<]*>)*[^<>]*$)`, "ig");
    return markup(
        odoomark(text).toString().replaceAll(regex, `<span class="${classes}">$1</span>`)
    );
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
