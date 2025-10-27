import { normalize } from "@web/core/l10n/utils";

/**
 * @param {string} pattern
 * @param {string|string[]} strs
 * @returns {number}
 */
function match(pattern, strs) {
    if (!Array.isArray(strs)) {
        strs = [strs];
    }
    let globalScore = 0;
    for (const str of strs) {
        globalScore = Math.max(globalScore, _match(pattern, str));
    }
    return globalScore;
}

/**
 * This private function computes a score that represent the fact that the
 * string contains the pattern, or not
 *
 * - If the score is 0, the string does not contain the letters of the pattern in
 *   the correct order.
 * - if the score is > 0, it actually contains the letters.
 *
 * Better matches will get a higher score: consecutive letters are better,
 * and a match closer to the beginning of the string is also scored higher.
 *
 * @param {string} pattern
 * @param {string} str
 * @returns {number}
 */
function _match(pattern, str) {
    let totalScore = 0;
    let currentScore = 0;
    let patternIndex = 0;

    pattern = normalize(pattern);
    str = normalize(str);

    const len = str.length;

    for (let i = 0; i < len; i++) {
        if (str[i] === pattern[patternIndex]) {
            patternIndex++;
            currentScore += 100 + currentScore - i / 200;
        } else {
            currentScore = 0;
        }
        totalScore = totalScore + currentScore;
    }

    return patternIndex === pattern.length ? totalScore : 0;
}

/**
 * Return a list of things that matches a pattern, ordered by their 'score' (
 * higher score first). An higher score means that the match is better. For
 * example, consecutive letters are considered a better match.
 *
 * @template T
 * @param {string} pattern
 * @param {T[]} list
 * @param {(element: T) => (string|string[])} fn
 * @returns {T[]}
 */
export function fuzzyLookup(pattern, list, fn) {
    const results = [];
    list.forEach((data) => {
        const score = match(pattern, fn(data));
        if (score > 0) {
            results.push({ score, elem: data });
        }
    });

    // we want better matches first
    results.sort((a, b) => b.score - a.score);

    return results.map((r) => r.elem);
}

// Does `pattern` fuzzy match `string`?
/**
 * @param {string} pattern
 * @param {string} string
 * @returns {boolean}
 */
export function fuzzyTest(pattern, string) {
    return _match(pattern, string) !== 0;
}

/**
 * Performs fuzzy matching using a Levenshtein distance algorithm
 * to find matches within an error margin between a pattern
 * and a list of words.
 *
 * If the pattern is found directly inside an item,
 * it's treated as a perfect match (score 0).
 * Otherwise, the `getScore` function calculates the distance
 * between the pattern and each candidate
 *
 * @param {string} pattern - The string to match.
 * @param {string[]} list - The list of strings to compare against the pattern.
 * @param {number} errorRatio - Controls how many errors can a word have depending of its length.
 * @returns {string[]} The list of the words that matches within a defined number of errors.
 */
export function fuzzyLevenshteinLookup(pattern, list, errorRatio = 3) {
    // We limit the maximum number of errors depending on the word length
    // to not have "overcorrections" into words that doesn't have anything
    // in common with what the user typed
    const maxNbrCorrection = Math.round(pattern.length / errorRatio);
    const results = [];
    list.forEach((candidate) => {
        let score = -1;
        if (candidate.includes(pattern)) {
            score = 0;
            results.push({ score, elem: pattern });
        } else {
            score = getLevenshteinScore(pattern, candidate);
            if (score >= 0 && score <= maxNbrCorrection) {
                results.push({ score, elem: candidate });
            }
        }
    });
    results.sort((a, b) => a.score - b.score);
    return results.map((r) => r.elem);
}


/**
 * Computes the Levenshtein distance between two strings.
 *
 * @param {string} a
 * @param {string} b
 * @returns {number} The Levenshtein distance between `a` and `b`.
 */
function getLevenshteinScore(a, b) {
    let aLength = a.length;
    let bLength = b.length;

    let distanceMatrix = [];
    for (let i = 0; i <= aLength; i++) {
        distanceMatrix[i] = [];
        for (let j = 0; j <= bLength; j++) {
            distanceMatrix[i][j] = 0;
        }
    }

    for (let i = 0; i <= aLength; i++) {
        for (let j = 0; j <= bLength; j++) {
            if (Math.min(i, j) === 0) {
                distanceMatrix[i][j] = Math.max(i, j);
            } else {
                if (a[i - 1] === b[j - 1]) {
                    distanceMatrix[i][j] = distanceMatrix[i - 1][j - 1];
                } else {
                    distanceMatrix[i][j] = Math.min(
                        distanceMatrix[i - 1][j] + 1,
                        distanceMatrix[i][j - 1] + 1,
                        distanceMatrix[i - 1][j - 1] + 1
                    );
                }
            }
        }
    }
    return distanceMatrix[aLength][bLength];
}
