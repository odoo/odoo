import {
    changeOption,
    clickOnSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("snippet_disclaimer", {
    url: "/",
    edition: true,
}, () => [
    {
        trigger: "#oe_snippets .oe_snippet[name='Disclaimer'].o_we_draggable .oe_snippet_thumbnail",
        run: "drag_and_drop :iframe #wrapwrap #o_snippet_above_header",
    },
    ...clickOnSnippet({ id: "s_disclaimer", name: "Disclaimer" }),
    changeOption("Disclaimer", "we-select:has([data-move-block]) we-toggler"),
    changeOption("Disclaimer", 'we-button[data-move-block="currentPage"]'),
    {
        content: "Check whether snippet moved to #wrap",
        trigger: ":iframe #wrap .s_disclaimer",
    },
]);
