import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("searchbar_in_translated_website", {}, () => [
    {
        content: "Wait for the page to load with the french locale.",
        trigger: "html[lang*='fr']",
    },
    {
        content: "Click the search button to open the search dialog.",
        trigger: ".o_searchbar_form a.o_search_btn",
        run: "click",
    },
    {
        content: "Verify the search dialog is opened.",
        trigger: "#o_search_modal .o_searchbar_form",
    },
]);
