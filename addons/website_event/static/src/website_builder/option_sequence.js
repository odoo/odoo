import { DEFAULT, END, splitBetween } from "@html_builder/utils/option_sequence";

const EVENT_PAGE = DEFAULT;
const [EXHIBITOR_FILTER, EVENT_PAGE_MAIN, SPONSOR, TRACK, ...__DETECT_ERROR_1__] = splitBetween(
    EVENT_PAGE,
    END,
    4
);
if (__DETECT_ERROR_1__.length > 0) {
    console.error("Wrong count in split after EVENT_PAGE_MAIN");
}
export { EVENT_PAGE, EXHIBITOR_FILTER, SPONSOR, TRACK, EVENT_PAGE_MAIN };
