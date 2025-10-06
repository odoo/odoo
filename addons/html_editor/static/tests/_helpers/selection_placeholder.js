import { unformat } from "./format";

/**
 * Get the HTML of a selection placeholder.
 *
 * @param {Object} param0
 * @param {boolean} [param0.selected=false]
 * @param {"p"|"div"} [param0.tag="p"]
 * @returns {string}
 */
export const PLACEHOLDER = ({ selected = false, tag = "p" } = {}) => {
    tag = tag.toLowerCase();
    const opening = tag === "p" ? "p" : 'div class="o-paragraph"';
    if (selected) {
        return `<${opening} data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></${tag}>`;
    } else {
        return `<${opening} data-selection-placeholder=""><br></${tag}>`;
    }
};

/**
 * Return the given HTML wrapped between two selection placeholders.
 *
 * @param {string} html
 * @param {Object} param1
 * @param {"p"|"div"} [param1.tag="p"]
 * @param {boolean} [param1.doUnformat=false]
 * @returns {string}
 */
export const wrapInPlaceholders = (html, { tag = "p", doUnformat = false } = {}) => {
    const output = PLACEHOLDER({ tag }) + html + PLACEHOLDER({ tag });
    return doUnformat ? unformat(output) : output;
};

/**
 * Selector for a paragraph that isn't a selection placeholder.
 */
export const TRUE_PARAGRAPH = "p:not([data-selection-placeholder])";
