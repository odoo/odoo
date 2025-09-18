// @ts-check

/** @module @web/core/l10n/utils/normalize - Unicode normalization, case folding, and accent-insensitive string matching */

/**
 * @typedef {{
 *  match: string;
 *  start: number;
 *  end: number;
 * }} NormalizedMatchResult
 */

/**
 * Normalizes a string for use in comparison.
 *
 * @example
 * normalize("déçûmes") === normalize("DECUMES")
 * normalize("𝔖𝔥𝔯𝔢𝔨") === normalize("Shrek")
 * normalize("Scleßin") === normalize("Sclessin")
 * normalize("Œdipe") === normalize("OeDiPe")
 *
 * @param {string} str
 * @returns {string}
 */
export function normalize(str) {
    return casefold(unaccent(expandLigatures(str.normalize("NFKC"))));
}

/**
 * Searches for "substr" in "src". The search is performed on normalized strings
 * so that "ce" can match "Cédric".
 *
 * @param {string} src
 * @param {string} substr
 * @returns {NormalizedMatchResult}
 */
export function normalizedMatch(src, substr) {
    if (!substr) {
        return { start: 0, end: 0, match: "" };
    }
    /**
     * Array.from splits the string into an array of codepoints. This avoids
     * processing unpaired surrogates, which could lead to unexpected results.
     *
     * "𝔖"[0];              // "\ud835" ← unpaired surrogate!!
     * Array.from("𝔖")[0];  // "𝔖"
     *
     * "𝔖".split("");   // Array [ "\ud835", "\udd16" ]
     * Array.from("𝔖"); // Array [ "𝔖" ]
     *
     * "𝔖".split("").map((c) => c.normalize("NFKC")).join("");      // "𝔖"
     * Array.from("𝔖").map((c) => c.normalize("NFKC")).join("");    // "S"
     */
    const srcAsCodepoints = Array.from(src);
    /**
     * Instead of calling normalize directly on the source string, the source is
     * split into an array of codepoints, where each of the elements is
     * normalized individually. This is because this function is expected to
     * return the start and end indexes of the match in the *original*,
     * unnormalized string, but strings can grow in length during normalization,
     * which would alter the indexes. Now, even if the length of the individual
     * elements grows, the length of the containing array remains the same.
     */
    const normalizedSrc = srcAsCodepoints.map(normalize);
    const normalizedSubstr = Array.from(normalize(substr));
    /**
     * normalizedSrc can contain empty strings if the source is an NFD string,
     * corresponding to diacritics that have been stripped off. They must be
     * taken into account in the length calculation to get the indexes right,
     * hence Math.max(x.length, 1).
     */
    const flattenSrcLength = normalizedSrc.reduce(
        (acc, x) => acc + Math.max(x.length, 1),
        0,
    );
    for (let i = 0; i <= flattenSrcLength - normalizedSubstr.length; ++i) {
        const substrStack = Array.from(normalizedSubstr).toReversed();
        for (let j = 0; i + j < normalizedSrc.length; ++j) {
            const current = normalizedSrc[i + j];
            // "every" in case normalization expanded current to several chars
            if (
                ![...current].every(
                    (c) => substrStack.length === 0 || c === substrStack.pop(),
                )
            ) {
                break;
            }
            if (substrStack.length === 0) {
                // full substring matched, return the result 😤
                const start = srcAsCodepoints.slice(0, i).join("").length;
                const match = srcAsCodepoints.slice(i, i + j + 1).join("");
                const end = start + match.length;
                return { start, end, match };
            }
        }
    }
    return { start: -1, end: -1, match: "" };
}

/**
 * Searches for "substr" in "src" as is done in normalizedMatch
 * but returns an array of all successful matches
 *
 * @param {string} src
 * @param {string} substr
 * @returns {NormalizedMatchResult[]}
 */
export function normalizedMatches(src, substr) {
    const matches = [];
    let index = 0;
    while (src.length) {
        const { start, end, match } = normalizedMatch(src, substr);
        if (match) {
            matches.push({ start: index + start, end: index + end, match });
            index += end;
            src = src.slice(end);
        } else {
            break;
        }
    }
    return matches;
}

const DECOMPOSITION_BY_LIGATURE = new Map([
    ["Æ", "Ae"], // Danish, Norwegian, Icelandic, French (rare)...
    ["æ", "ae"],
    ["Œ", "Oe"], // French: "Richard Cœur de Lion"
    ["œ", "oe"],
    ["Ĳ", "IJ"], // Dutch: "IJzer"
    ["ĳ", "ij"],
]);

/**
 * Splits ligatures into their constituent glyphs, e.g. turns Œ into Oe.
 *
 * @param {string} str
 * @returns {string}
 */
function expandLigatures(str) {
    return Array.from(str, (char) => DECOMPOSITION_BY_LIGATURE.get(char) ?? char).join(
        "",
    );
}

/**
 * Diacritics are marks, such as accents or cedilla, that when added to a letter
 * change its pronunciation or meaning. Unicode has a category for them, but it
 * doesn't consider characters like "ø" to be a diacritical "o". Below is a list
 * of characters that could be considered "diacritical characters" but aren't
 * labeled as such by Unicode.
 */
const DIACRITIC_LIKES = new Map([
    ["Ø", "O"], // notably used in Danish and Norwegian: "Jørgen"
    ["ø", "o"],
    ["Ł", "L"], // notably used in Polish: "Paweł"
    ["ł", "l"],
    ["Ð", "D"], // Icelandic, "Borgarfjörður"
    ["ð", "d"],
    ["Ħ", "H"], // Maltese, "Ħamrun Spartans Football Club"
    ["ħ", "h"],
    ["Ŧ", "T"], // apparently used in Sámi languages, very few speakers
    ["ŧ", "t"],
]);

/**
 * Removes "diacritics" (funny marks added to letters, such as accents and
 * cedillas) from a string.
 *
 * @param {string} str
 * @returns {string}
 */
function unaccent(str) {
    return Array.from(
        str.normalize("NFD").replace(/\p{Nonspacing_Mark}/gu, ""),
        (char) => DIACRITIC_LIKES.get(char) ?? char,
    ).join("");
}

/**
 * Normalizes string case for use in comparison.
 *
 * Some characters change length when converted from one case to another. A
 * common example is the German letter "ß," which becomes "SS" when uppercased.
 * This function ensures that these special cases are handled correctly.
 *
 * ⚠ Doesn't preserve "Turkish I"s.
 *
 * @see https://www.w3.org/TR/charmod-norm/#definitionCaseFolding
 * @see https://www.unicode.org/Public/UNIDATA/CaseFolding.txt
 *
 * @example
 * casefold("AAAAAAAA")                 // "aaaaaaaa"
 * casefold("և")                        // "ԵՒ"
 * casefold("Kevin Großkreutz")         // "kevin grosskreutz"
 * casefold("Diyarbakır")               // "diyarbakir"
 * casefold("ß") !== "ß".toLowerCase()  // true
 * casefold("ß") === casefold("SS")     // true
 *
 * @param {string} str
 * @returns {string} lowercase string after "full case folding"
 */
function casefold(str) {
    return str.toLowerCase().toUpperCase().toLowerCase();
}
