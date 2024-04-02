/** @odoo-module **/
import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("snippet_rating", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({ id: "s_rating", name: "Rating" }),
    wTourUtils.clickOnSnippet({ id: "s_rating", name: "Rating" }),
    wTourUtils.changeOption("Rating", "we-select:has([data-select-class]) we-toggler"),
    wTourUtils.changeOption("Rating", 'we-button[data-select-class="s_rating_inline"]'),
    {
        content: "Check whether s_rating_inline class applied or not",
        trigger: ":iframe .s_rating_inline",
        isCheck: true
    },
    wTourUtils.changeOption("Rating", "we-select:has([data-select-class]) we-toggler"),
    wTourUtils.changeOption("Rating", 'we-button[data-select-class="s_rating_no_title"]'),
    {
        content: "Check whether s_rating_no_title class applied or not",
        trigger: ":iframe .s_rating_no_title",
        isCheck: true,
    },
    wTourUtils.changeOption("Rating", "we-select:has([data-select-class]) we-toggler"),
    wTourUtils.changeOption("Rating", 'we-button[data-select-class=""] div:contains("Top")'),
    {
        content: "Check whether s_rating_no_title class removed or not",
        trigger: ":iframe .s_rating:not(.s_rating_no_title)",
        isCheck: true,
    },
]);
