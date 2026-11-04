/**
 * Detection of Markdown in pasted text. The conversion to HTML is done by the
 * server (see `/html_editor/markdown_to_html`).
 */

const TABLE_DELIMITER_REGEX = /^ {0,3}\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$/;

// Heuristics used to detect Markdown in pasted text. Only syntax that is
// unlikely to appear in regular text is considered (e.g. a lone `*italic*` or
// `__init__` is not enough).
const DETECTION_BLOCK_REGEXES = [
    /^ {0,3}#{1,6}[ \t]+\S/, // heading
    /^ {0,3}(`{3,}|~{3,})/, // fenced code block
    /^ {0,3}> ?\S/, // blockquote
    /^ *[-*+] \[[ xX]\](?:[ \t]|$)/, // task list item
];
const DETECTION_LIST_ITEM_REGEX = /^ *(?:[-*+]|\d{1,9}[.)])[ \t]+\S/;
const DETECTION_INLINE_REGEX = new RegExp(
    [
        /!?\[[^\]\n]+\]\([^)\s]+(?:[ \t]+"[^"\n]*")?\)/.source, // link or image
        /\*\*(?=\S)[^\n]*?\S\*\*/.source, // strong
        /~~(?=\S)[^\n]*?\S~~/.source, // strikethrough
        /`[^`\n]+`/.source, // inline code
    ].join("|")
);

/**
 * Return true if the given text most likely contains Markdown syntax.
 *
 * @param {string} text
 * @returns {boolean}
 */
export function isMarkdown(text) {
    const lines = text.split(/\r\n?|\n/);
    let listItemCount = 0;
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (DETECTION_BLOCK_REGEXES.some((regex) => regex.test(line))) {
            return true;
        }
        if (isTableStart(lines, i)) {
            return true;
        }
        if (DETECTION_LIST_ITEM_REGEX.test(line) && ++listItemCount > 1) {
            return true;
        }
    }
    return DETECTION_INLINE_REGEX.test(text);
}

/**
 * Split a table row into its cells, taking escaped pipes into account.
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
    const cells = [];
    let cell = "";
    for (let i = 0; i < row.length; i++) {
        if (row[i] === "\\" && row[i + 1] === "|") {
            cell += "|";
            i++;
        } else if (row[i] === "|") {
            cells.push(cell.trim());
            cell = "";
        } else {
            cell += row[i];
        }
    }
    cells.push(cell.trim());
    return cells;
}

function isTableStart(lines, index) {
    const delimiterRow = lines[index + 1];
    return (
        lines[index].includes("|") &&
        delimiterRow !== undefined &&
        delimiterRow.includes("|") &&
        TABLE_DELIMITER_REGEX.test(delimiterRow) &&
        splitTableRow(lines[index]).length === splitTableRow(delimiterRow).length
    );
}
