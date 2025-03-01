import { user } from "@web/core/user";

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
 * Format the items in `list` as a list in a locale-dependent manner with the chosen style.
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
 * See https://www.unicode.org/reports/tr35/tr35-49/tr35-general.html#ListPatterns for more details.
 *
 * @param {string[]} list The array of values to format into a list.
 * @param {Object} [param0]
 * @param {string} [param0.localeCode] The locale to use (e.g. en-US).
 * @param {"standard"|"standard-short"|"or"|"or-short"|"unit"|"unit-short"|"unit-narrow"} [param0.style="standard"] The style to format the list with.
 * @returns {string} The formatted list.
 */
export function formatList(list, { localeCode = "", style = "standard" } = {}) {
    const locale = localeCode || user.lang || "en-US";
    const formatter = new Intl.ListFormat(locale, LIST_STYLES[style]);
    return formatter.format(Array.from(list, String));
}
