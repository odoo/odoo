import {
    splitBetween,
    SNIPPET_SPECIFIC_AFTER,
    VERTICAL_ALIGNMENT,
    LAYOUT_COLUMN,
    SNIPPET_SPECIFIC_NEXT,
    SNIPPET_SPECIFIC_END,
    END,
} from "@html_builder/utils/option_sequence";

// Gives names to website options sequence.
const [WEBSITE_BACKGROUND_OPTIONS, BOX_BORDER_SHADOW, LAYOUT, ...__DETECT_ERROR_WEBSITE_0__] =
    splitBetween(SNIPPET_SPECIFIC_AFTER, LAYOUT_COLUMN, 3);
if (__DETECT_ERROR_WEBSITE_0__.length > 0) {
    console.error("Wrong count in website split after specific");
}
const [LAYOUT_GRID, ...__DETECT_ERROR_WEBSITE_1__] = splitBetween(
    LAYOUT_COLUMN,
    VERTICAL_ALIGNMENT,
    1
);
if (__DETECT_ERROR_WEBSITE_1__.length > 0) {
    console.error("Wrong count in website split after column layout");
}
const [GRID_COLUMNS, ...__DETECT_ERROR_WEBSITE_2__] = splitBetween(
    VERTICAL_ALIGNMENT,
    SNIPPET_SPECIFIC_NEXT,
    1
);
if (__DETECT_ERROR_WEBSITE_2__.length > 0) {
    console.error("Wrong count in website split after vertical alignment");
}
export {
    WEBSITE_BACKGROUND_OPTIONS,
    BOX_BORDER_SHADOW,
    LAYOUT,
    LAYOUT_COLUMN,
    LAYOUT_GRID,
    GRID_COLUMNS,
};
const [COVER_PROPERTIES, CONTAINER_WIDTH, SCROLL_BUTTON, ...__DETECT_ERROR_WEBSITE_3__] =
    splitBetween(SNIPPET_SPECIFIC_NEXT, SNIPPET_SPECIFIC_END, 3);
if (__DETECT_ERROR_WEBSITE_3__.length > 0) {
    console.error("Wrong count in website split before specific end");
}
export { COVER_PROPERTIES, CONTAINER_WIDTH, SCROLL_BUTTON };
const [
    GRID_IMAGE,
    TEXT_HIGHLIGHT,
    ANIMATE,
    CONDITIONAL_VISIBILITY,
    DEVICE_VISIBILITY,
    ...__DETECT_ERROR_WEBSITE_4__
] = splitBetween(SNIPPET_SPECIFIC_END, END, 5);
if (__DETECT_ERROR_WEBSITE_4__.length > 0) {
    console.error("Wrong count in website split after specific end");
}
export { GRID_IMAGE, TEXT_HIGHLIGHT, ANIMATE, CONDITIONAL_VISIBILITY, DEVICE_VISIBILITY };
