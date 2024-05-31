/**
 * @typedef {Object} SuggestionTrigger
 * @property {string} pattern A regex string that defines the start of
 * a suggestion.
 * @property {number} [startIndex] The position of the delimiter in the text. If
 * omitted, any position is allowed.
 * @property {string} [endPattern] A regex string that defines when to stop
 * matching a suggestion. If omitted, two consecutive spaces are considered the
 * end of the suggestion.
 * @property {string} id A unique id used to identify delimiters
 */

/**
 * @typedef {Object} SuggestionMatch
 * @property {string} term
 * @property {string} delimiter id of the delimiter related     to the match.
 * @property {number} start
 * @property {number} end
 */

/**
 *
 * @param {SuggestionTrigger[]} triggers
 * @returns {{id: string, regex: RegExp }[]}
 */
function generateRegexesFromTriggers(triggers) {
    const result = [];
    for (const delimiter of triggers) {
        const endDelimiter = delimiter.endPattern ?? "\\s{2,}";
        const endPattern = `${endDelimiter}|${triggers.map((d) => `\\s${d.pattern}`).join("|")}`;
        const startPattern =
            delimiter.startIndex === 0
                ? "^"
                : delimiter.startIndex
                ? `.{${delimiter.startIndex}}\\s`
                : "(?<=^|\\s)";
        const regex = new RegExp(
            `${startPattern}(?<delimiter>${delimiter.pattern})(?<term>(?:(?!${endPattern}).)*)`,
            "g"
        );
        result.push({ id: delimiter.id, regex: regex });
    }
    return result;
}

/**
 * @param {string} text
 * @param {SuggestionTrigger[]} triggers
 * @return {SuggestionMatch[]}
 */
export function extractSuggestions(text, triggers) {
    const parsed = generateRegexesFromTriggers(triggers);
    const matches = [];
    for (const { id, regex } of parsed) {
        let match;
        while ((match = regex.exec(text))) {
            matches.push({
                end: regex.lastIndex,
                start: regex.lastIndex - match[0].length,
                term: match.groups.term,
                delimiter: id,
            });
        }
    }
    return matches;
}
