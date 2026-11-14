const TABLE_DELIMITER_REGEX = /^ {0,3}\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*(?:\|[ \t]*)?$/;

const DETECTION_REGEXES = [
    /^#{1,6}[ \t]+\S/m, // heading
    /^ {0,3}>[ \t]*\S/m, // blockquote
    /^ *(?:[-*+]|\d{1,9}\.)[ \t]+\S/m, // list item
    /!?\[[^[\]\n]+\]\([^)\s]+(?:[ \t]+"[^"\n]*")?\)/, // link or image
    /\*\*(?=\S)[^\n]*?\S\*\*/, // strong
    /~~(?=\S)[^\n]*?\S~~/, // strikethrough
    /`[^`\n]+`/, // inline code
];
const DETECTION_CODE_BLOCK_DELIMITER_REGEX = /^ {0,3}`{3,}/;

/**
 * Return true if the given text most likely contains Markdown syntax.
 *
 * @param {string} text
 * @returns {boolean}
 */
export function isMarkdown(text) {
    if (DETECTION_REGEXES.some((regex) => regex.test(text))) {
        return true;
    }
    const lines = text.split(/\r\n?|\n/);
    let codeBlockDelimiterCount = 0;
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // A lone delimiter isn't converted.
        if (DETECTION_CODE_BLOCK_DELIMITER_REGEX.test(line) && ++codeBlockDelimiterCount > 1) {
            return true;
        }
        if (isTableStart(lines, i)) {
            return true;
        }
    }
    return false;
}

/**
 * Split a table row into its cells, ignoring escaped pipes.
 *
 * @param {string} line
 * @returns {string[]}
 */
function splitTableRow(line) {
    let row = line.trim();
    if (row.startsWith("|")) {
        row = row.slice(1);
    }
    if (row.endsWith("|") && !row.endsWith("\\|")) {
        row = row.slice(0, -1);
    }
    return row.split(/(?<!\\)\|/);
}

/**
 * Return true if a table starts at the given line: a header row after a blank
 * line, followed by a delimiter row with as many cells and at least one row.
 *
 * @param {string[]} lines
 * @param {number} index
 * @returns {boolean}
 */
function isTableStart(lines, index) {
    const delimiterRow = lines[index + 1];
    const firstRow = lines[index + 2];
    return (
        (index === 0 || !lines[index - 1].trim()) &&
        lines[index].includes("|") &&
        delimiterRow !== undefined &&
        delimiterRow.includes("|") &&
        TABLE_DELIMITER_REGEX.test(delimiterRow) &&
        splitTableRow(lines[index]).length === splitTableRow(delimiterRow).length &&
        firstRow !== undefined &&
        firstRow.includes("|")
    );
}
