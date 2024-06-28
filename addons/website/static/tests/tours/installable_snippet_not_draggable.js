/** @odoo-module **/
import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("installable_snippet_not_draggable", {
    url: "/",
    test: true,
    edition: true,
}, () => [
    wTourUtils.dragNDrop({ name: "Fake Snippet" }),
    {
        content: "Check that the snippet is not in the page",
        trigger: "iframe body",
        run: ({ tip_widget }) => {
            if (tip_widget.$anchor[0].querySelector("[data-name='Fake Snippet']")) {
                throw new Error("The snippet should not be in the page");
            }
        }
    }
]);
