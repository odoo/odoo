/**
 * @typedef {{
 *  match: string;
 *  start: number;
 *  end: number;
 * }} NormalizedMatchResult
 */

/**
 * Normalizes a string for use in comparison.
 * Handles ligatures, compatibility symbols, diacritics, and French/German accents.
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

const CUSTOM_FOLDINGS = {
    ß: "ss", // German (Eszett): "Großmann", "Straße"
    æ: "ae", // Danish, Norwegian, Icelandic: "Ærøskøbing", "Læse"
    œ: "oe", // French (ligature): "Cœur", "Œil"
    ø: "o", // Danish, Norwegian, Faroese: "Tromsø", "København"
    ħ: "h", // Maltese: "Ħamrun", "Ħelu" (sweet)
    đ: "d", // Serbo-Croatian, Vietnamese: "Đurađ", "Đakovo"
    ð: "d", // Icelandic, Faroese (Eth): "Borgarfjörður", "Suðuroy"
    ł: "l", // Polish, Sorbian: "Paweł", "Łódź"
    ŋ: "n", // Sami, Dinka: "Nuŋ" (Dinka name), "Uiŋ" (Sami: "of the night")
    ŧ: "t", // Northern Sami: "itŧin" (tomorrow), "mátŧi" (capable)
    þ: "th", // Icelandic, Old English (Thorn): "Þingvellir", "Þorlákshöfn"
    "·": "", // Catalan (Middle Dot): ensures "paral·lel"
    ŀ: "l", // Catalan (L with middle dot): "paral·lel", "col·lecció"
    ı: "i", // Turkish (Dotless I): "Diyarbakır", "ılık" (warm)
};

// Pre-compiled regex for atomic characters that don't decompose via NFKD
const FOLDING_REGEX = new RegExp(`[${Object.keys(CUSTOM_FOLDINGS).join("")}]`, "gu");

// Targets common combining marks (accents) and format chars,
// but avoids the Brahmic/Indic ranges to preserve script integrity.
const STRIP_REGEX = /[\u0300-\u036f\p{Cf}]/gu;

// Standard US-ASCII character set (codes from 32 to 126):
// Lowercase letters: a to z
// Uppercase letters: A to Z
// Digits: 0 to 9
// Space
// Standard Punctuation: ! " # $ % & ' ( ) * + , - . / : ; < = > ? @ [ \ ] ^ _  { | } ~`
const ASCII_SAFE_REGEX = /^[\x20-\x7E]*$/;

export function normalize(str) {
    if (!str) {
        return "";
    }

    // Fast check
    if (ASCII_SAFE_REGEX.test(str)) {
        return str.toLowerCase();
    }

    return (
        str
            // 1. Decompose: splits 'é' into 'e + ´' and expands symbols like '㎩' to 'Pa'
            .normalize("NFKD")
            // 2. Strip Marks: removes all 'floating' Unicode marks (accents marks) and format characters
            .replace(STRIP_REGEX, "")
            // 3. Standardize case for comparison
            .toLowerCase()
            // 4. Atomic Foldings: manually convert unique letters (like 'ø' or 'ß') to ASCII
            .replace(FOLDING_REGEX, (m) => CUSTOM_FOLDINGS[m])
    );
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
    const flattenSrcLength = normalizedSrc.reduce((acc, x) => acc + Math.max(x.length, 1), 0);
    for (let i = 0; i <= flattenSrcLength - normalizedSubstr.length; ++i) {
        const substrStack = Array.from(normalizedSubstr).reverse();
        for (let j = 0; i + j < normalizedSrc.length; ++j) {
            const current = normalizedSrc[i + j];
            // "every" in case normalization expanded current to several chars
            if (![...current].every((c) => substrStack.length === 0 || c === substrStack.pop())) {
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
