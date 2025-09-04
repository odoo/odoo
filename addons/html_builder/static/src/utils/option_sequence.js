// Gives names to options sequence.
// Module-specific sequences are defined in other option_sequence.js files.

const BEGIN = 1;
const END = 100;

/** Ordered set of known positions. */
const ALL = [BEGIN, END];
/**
 * This position should be used for non-snippet options.
 * For the default position of snippet specific options, use {@link SNIPPET_SPECIFIC}.
 */
export const DEFAULT = track(10);

/**
 * Keeps track of a position in the ordered list positions ALL.
 *
 * @param {Number} position
 * @return {Number} position parameter itself
 */
function track(position) {
    if (!(position in ALL)) {
        const index = ALL.findIndex((value) => value > position);
        if (index === -1) {
            ALL.push(position);
        } else {
            ALL.splice(index, 0, position);
        }
    }
    return position;
}
/**
 * Generates 'count' positions evenly-spread between a beginPosition and an
 * endPosition.
 *
 * @param {Number} beginPosition position after which to generate positions
 * @param {Number} endPosition position before which to generate positions
 * @param {int} count amount of generated positions
 * @return {Number[]} containing {@link count} positions generated within range
 */
export function splitBetween(beginPosition, endPosition, count) {
    const result = [];
    const delta = (endPosition - beginPosition) / (count + 1);
    for (let index = 1; index <= count; index++) {
        result.push(track(beginPosition + delta * index));
    }
    return result;
}
/**
 * Generates a position halfway between two positions.
 *
 * @param {Number} previousPosition position after which to generate position
 * @param {Number} nextPosition position before which to generate position
 * @return {Number} position halfway between begin and end
 */
export function between(previousPosition, nextPosition) {
    return splitBetween(previousPosition, nextPosition, 1)[0];
}
/**
 * Generates a position after the specified position, but before the next
 * already known position.
 *
 * @param {Number} position position after which to generate position
 * @return {Number} generated position
 */
export function after(position) {
    const index = ALL.findIndex((value) => value === position);
    if (index === -1) {
        throw new Error("Position " + position + " does not exist. Do not use arbitrary numbers.");
    }
    if (index === ALL.length - 1) {
        throw new Error("Cannot place something after END position.");
    }
    const nextPosition = ALL[index + 1];
    return between(position, nextPosition);
}
/**
 * Generates a position before the specified position, but after the previous
 * already known position.
 *
 * @param {Number} position position before which to generate position
 * @return {Number} generated position
 */
export function before(position) {
    const index = ALL.findIndex((value) => value === position);
    if (index === -1) {
        throw new Error("Position " + position + " does not exist. Do not use arbitrary numbers.");
    }
    if (index === 0) {
        throw new Error("Cannot place something before BEGIN position.");
    }
    const previousPosition = ALL[index - 1];
    return between(previousPosition, position);
}

const SNIPPET_SPECIFIC = DEFAULT;
const [
    REPLACE_MEDIA,
    FONT_AWESOME,
    IMAGE_TOOL,
    ALIGNMENT_STYLE_PADDING,
    DYNAMIC_SVG,
    AFTER_HTML_BUILDER,
    SNIPPET_SPECIFIC_BEFORE,
    ...__DETECT_ERROR_1__
] = splitBetween(BEGIN, SNIPPET_SPECIFIC, 7);
if (__DETECT_ERROR_1__.length > 0) {
    console.error("Wrong count in split before default");
}

const [
    SNIPPET_SPECIFIC_AFTER,
    LAYOUT_COLUMN,
    VERTICAL_ALIGNMENT,
    SNIPPET_SPECIFIC_NEXT,
    SNIPPET_SPECIFIC_END,
    ANIMATE,
    ...__DETECT_ERROR_2__
] = splitBetween(SNIPPET_SPECIFIC, END, 6);
if (__DETECT_ERROR_2__.length > 0) {
    console.error("Wrong count in split after default");
}

const [TEXT_ALIGNMENT, TITLE_LAYOUT_SIZE, WIDTH, BLOCK_ALIGN, ...__DETECT_ERROR_3__] = splitBetween(
    AFTER_HTML_BUILDER,
    SNIPPET_SPECIFIC_BEFORE,
    4
);
if (__DETECT_ERROR_3__.length > 0) {
    console.error("Wrong count in website split before specific");
}
export { TEXT_ALIGNMENT, TITLE_LAYOUT_SIZE, WIDTH, BLOCK_ALIGN };

export {
    BEGIN,
    REPLACE_MEDIA,
    FONT_AWESOME,
    IMAGE_TOOL,
    ALIGNMENT_STYLE_PADDING,
    DYNAMIC_SVG,
    AFTER_HTML_BUILDER,
    SNIPPET_SPECIFIC_BEFORE,
    SNIPPET_SPECIFIC,
    SNIPPET_SPECIFIC_AFTER,
    LAYOUT_COLUMN,
    VERTICAL_ALIGNMENT,
    SNIPPET_SPECIFIC_NEXT,
    SNIPPET_SPECIFIC_END,
    ANIMATE,
    END,
};
