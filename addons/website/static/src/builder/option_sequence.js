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
const [LAYOUT, ...__DETECT_ERROR_WEBSITE_0__] = splitBetween(
    SNIPPET_SPECIFIC_AFTER,
    LAYOUT_COLUMN,
    1
);
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
const [WEBSITE_BACKGROUND_OPTIONS, GRID_COLUMNS, BOX_BORDER_SHADOW, ...__DETECT_ERROR_WEBSITE_2__] =
    splitBetween(VERTICAL_ALIGNMENT, SNIPPET_SPECIFIC_NEXT, 3);
if (__DETECT_ERROR_WEBSITE_2__.length > 0) {
    console.error("Wrong count in website split after vertical alignment");
}
export {
    LAYOUT,
    LAYOUT_COLUMN,
    LAYOUT_GRID,
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
