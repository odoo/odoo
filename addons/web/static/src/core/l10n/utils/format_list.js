import { user } from "@web/core/user";

/**
 * @typedef {keyof typeof LIST_STYLES} FormatListStyle
 */

/**
 * Convert Unicode TR35-49 list pattern types to ES Intl.ListFormat options
 */
const LIST_STYLES = {
    standard: {
        type: "conjunction",
        style: "long",
    },
    "standard-short": {
        type: "conjunction",
        style: "short",
    },
    or: {
        type: "disjunction",
        style: "long",
    },
    "or-short": {
        type: "disjunction",
        style: "short",
    },
    unit: {
        type: "unit",
        style: "long",
    },
    "unit-short": {
        type: "unit",
        style: "short",
    },
    "unit-narrow": {
        type: "unit",
        style: "narrow",
    },
};

/**
 * Format the items in `values` as a list in a locale-dependent manner with the
 * chosen style.
 *
 * The available styles are defined in the Unicode TR35-49 spec:
 * * standard:
 *   A typical "and" list for arbitrary placeholders.
 *   e.g. "January, February, and March"
 * * standard-short:
 *   A short version of an "and" list, suitable for use with short or abbreviated placeholder values.
 *   e.g. "Jan., Feb., and Mar."
 * * or:
 *   A typical "or" list for arbitrary placeholders.
 *   e.g. "January, February, or March"
 * * or-short:
 *   A short version of an "or" list.
 *   e.g. "Jan., Feb., or Mar."
 * * unit:
 *   A list suitable for wide units.
 *   e.g. "3 feet, 7 inches"
 * * unit-short:
 *   A list suitable for short units
 *   e.g. "3 ft, 7 in"
 * * unit-narrow:
 *   A list suitable for narrow units, where space on the screen is very limited.
 *   e.g. "3′ 7″"
 *
 * @see https://www.unicode.org/reports/tr35/tr35-general.html#ListPatterns for more details.
 *
 * @param {Iterable<string>} values values to format into a list.
 * @param {{
 *  localeCode?: string;
 *  style?: FormatListStyle;
 * }} [options]
 * @returns {string} formatted list.
 */
export function formatList(values, { localeCode, style } = {}) {
    const locale = localeCode || user.lang || "en-US";
    const formatter = new Intl.ListFormat(locale, LIST_STYLES[style || "standard"]);
    return formatter.format(Array.from(values, String));
}
