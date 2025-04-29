import {
    splitBetween,
    AFTER_HTML_BUILDER,
    SNIPPET_SPECIFIC_BEFORE,
    SNIPPET_SPECIFIC_AFTER,
    SNIPPET_SPECIFIC_NEXT,
    SNIPPET_SPECIFIC_END,
    END,
} from "@html_builder/utils/option_sequence";

// Gives names to website options sequence.

const [TEXT_ALIGNMENT, TITLE_LAYOUT_SIZE, WIDTH, BLOCK_ALIGN, ...__DETECT_ERROR_WEBSITE_1__] =
    splitBetween(AFTER_HTML_BUILDER, SNIPPET_SPECIFIC_BEFORE, 4);
if (__DETECT_ERROR_WEBSITE_1__.length > 0) {
    console.error("Wrong count in website split before specific");
}
export { TEXT_ALIGNMENT, TITLE_LAYOUT_SIZE, WIDTH, BLOCK_ALIGN };
const [
    LAYOUT,
    LAYOUT_COLUMN,
    LAYOUT_GRID,
    VERTICAL_ALIGNMENT,
    WEBSITE_BACKGROUND_OPTIONS,
    GRID_COLUMNS,
    BOX_BORDER_SHADOW,
    ...__DETECT_ERROR_WEBSITE_2__
] = splitBetween(SNIPPET_SPECIFIC_AFTER, SNIPPET_SPECIFIC_NEXT, 7);
if (__DETECT_ERROR_WEBSITE_2__.length > 0) {
    console.error("Wrong count in website split after specific");
}
export {
    LAYOUT,
    LAYOUT_COLUMN,
    LAYOUT_GRID,
    VERTICAL_ALIGNMENT,
    WEBSITE_BACKGROUND_OPTIONS,
    GRID_COLUMNS,
    BOX_BORDER_SHADOW,
};
const [
    COVER_PROPERTIES,
    CONTAINER_WIDTH,
    SCROLL_BUTTON,
    CONDITIONAL_VISIBILITY,
    DEVICE_VISIBILITY,
    ...__DETECT_ERROR_WEBSITE_3__
] = splitBetween(SNIPPET_SPECIFIC_NEXT, SNIPPET_SPECIFIC_END, 5);
if (__DETECT_ERROR_WEBSITE_3__.length > 0) {
    console.error("Wrong count in website split before specific end");
}
export {
    COVER_PROPERTIES,
    CONTAINER_WIDTH,
    SCROLL_BUTTON,
    CONDITIONAL_VISIBILITY,
    DEVICE_VISIBILITY,
};
const [GRID_IMAGE, ANIMATE, TEXT_HIGHLIGHT, ...__DETECT_ERROR_WEBSITE_4__] = splitBetween(
    SNIPPET_SPECIFIC_END,
    END,
    3
);
if (__DETECT_ERROR_WEBSITE_4__.length > 0) {
    console.error("Wrong count in website split after specific end");
}
export { GRID_IMAGE, ANIMATE, TEXT_HIGHLIGHT };
