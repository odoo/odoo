/** @odoo-module **/
import {
    changeOption,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("snippet_rating", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({ id: "s_rating", name: "Rating" }),
    ...clickOnSnippet({ id: "s_rating", name: "Rating" }),
    changeOption("Rating", "we-select:has([data-select-class]) we-toggler"),
    changeOption("Rating", 'we-button[data-select-class="s_rating_inline"]'),
    {
        content: "Check whether s_rating_inline class applied or not",
        trigger: ":iframe .s_rating_inline",
    },
    changeOption("Rating", "we-select:has([data-select-class]) we-toggler"),
    changeOption("Rating", 'we-button[data-select-class="s_rating_no_title"]'),
    {
        content: "Check whether s_rating_no_title class applied or not",
        trigger: ":iframe .s_rating_no_title",
    },
    changeOption("Rating", "we-select:has([data-select-class]) we-toggler"),
    changeOption("Rating", 'we-button[data-select-class=""] div:contains("Top")'),
    {
        content: "Check whether s_rating_no_title class removed or not",
        trigger: ":iframe .s_rating:not(.s_rating_no_title)",
    },
]);
