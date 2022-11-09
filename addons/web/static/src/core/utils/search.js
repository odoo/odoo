/** @odoo-module */

import { unaccent } from "./strings";

/**
 * This private function computes a score that represent the fact that the
 * searchData contains the pattern, or not
 *
 * - If the score is 0, the searchData does not contain the letters of the pattern in
 *   the correct order.
 * - if the score is > 0, it actually contains the letters.
 *
 * Better matches will get a higher score: consecutive letters are better,
 * and a match closer to the beginning of the matching keyword from searchData
 * is also scored higher.
 */
function match(pattern, searchData) {
    if (typeof searchData === 'string') {
        searchData = [ searchData ];
    }

    pattern = unaccent(pattern, false);
    const patternLen = pattern.length;
    let finalScore = 0;

    for (let keyword of searchData) {
        keyword = unaccent(keyword, false);
        let totalScore = 0;
        let currentScore = 0;
        const len = keyword.length;
        let patternIndex = 0;

        for (let i = 0; i < len; i++) {
            if (keyword[i] === pattern[patternIndex]) {
                patternIndex++;
                currentScore += 100 + currentScore - i / 200;
            } else {
                currentScore = 0;
            }
            totalScore = totalScore + currentScore;
        }

        finalScore = Math.max(finalScore, patternIndex === patternLen ? totalScore : 0);
    }

    return finalScore;
}

/**
 * Return a list of things that matches a pattern, ordered by their 'score' (
 * higher score first). An higher score means that the match is better. For
 * example, consecutive letters are considered a better match.
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
export function fuzzyTest(pattern, string) {
    return match(pattern, string) !== 0;
}
