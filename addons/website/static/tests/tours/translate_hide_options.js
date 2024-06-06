/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("translate_hide_options", {
    url: "/",
    test: true,
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: "s_cover",
        name: "Cover",
    }),
    {
        content: "Click on the snippet title",
        trigger: ":iframe .s_cover h1",
        run: "dblclick",
    },
    {
        content: "Click on the 'Animate Text' button to activate the option",
        trigger: "div.o_we_animate_text",
        run: "click",
    },
    {
        content: "Go to /fr",
        trigger: "body",
        run: () => {
            // After checking the presence of the editor dashboard, we visit a
            // translated version of the homepage. The homepage is a special
            // case (there is no trailing slash), so we test it separately.
            location.href = "/fr";
        },
    },
]);
