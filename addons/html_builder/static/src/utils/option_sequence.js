// Gives names to options sequence.

const BEGIN = 1;
const DEFAULT = 10;
const END = 100;

/** Ordered set of known positions. */
const ALL = [BEGIN, END];

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
export function splitBetween(beginPosition, endPosition, count) {
    const result = [];
    const delta = (endPosition - beginPosition) / (count + 1);
    for (let index = 1; index <= count; index++) {
        result.push(track(beginPosition + delta * index));
    }
    result.push(endPosition); // to detect errors
    return result;
}
export function between(previousPosition, nextPosition) {
    return splitBetween(previousPosition, nextPosition, 1)[0];
}
export function after(position) {
    const index = ALL.findIndex((value) => value === position);
    const nextPosition = ALL[index + 1];
    return between(position, nextPosition);
}
export function before(position) {
    const index = ALL.findIndex((value) => value === position);
    const previousPosition = ALL[index - 1];
    return between(previousPosition, position);
}

// TODO Find out what should be in the html_builder, and what should be in specific modules.

const SNIPPET_SPECIFIC = DEFAULT;
const [
    REPLACE_MEDIA,
    MEDIA_URL,
    FONT_AWESOME,
    IMAGE_TOOL,
    ALIGNMENT_STYLE_PADDING,
    DYNAMIC_SVG,
    AFTER_HTML_BUILDER,
    SNIPPET_SPECIFIC_BEFORE,
    __DETECT_ERROR_1__,
] = splitBetween(BEGIN, SNIPPET_SPECIFIC, 8);
if (__DETECT_ERROR_1__ !== SNIPPET_SPECIFIC) {
    console.error("Wrong count in split before default");
}
const [SNIPPET_SPECIFIC_AFTER, SNIPPET_SPECIFIC_NEXT, SNIPPET_SPECIFIC_END, __DETECT_ERROR_2__] =
    splitBetween(SNIPPET_SPECIFIC, END, 3);
if (__DETECT_ERROR_2__ !== END) {
    console.error("Wrong count in split after default");
}
export {
    BEGIN,
    REPLACE_MEDIA,
    MEDIA_URL,
    FONT_AWESOME,
    IMAGE_TOOL,
    ALIGNMENT_STYLE_PADDING,
    DYNAMIC_SVG,
    AFTER_HTML_BUILDER,
    SNIPPET_SPECIFIC_BEFORE,
    SNIPPET_SPECIFIC,
    SNIPPET_SPECIFIC_AFTER,
    SNIPPET_SPECIFIC_NEXT,
    SNIPPET_SPECIFIC_END,
    END,
};
