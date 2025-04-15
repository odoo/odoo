/** @odoo-module */

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("text_animations", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: "s_cover",
        name: "Cover",
    }),
    {
        content: "Click on the snippet title",
        trigger: "iframe .s_cover h1",
        run: "dblclick", // Make sure the title is selected.
    },
    {
        content: "Click on the 'Animate Text' button to activate the option",
        trigger: "div.o_we_animate_text",
    },
    {
        content: "Check that the animation was applied",
        trigger: "iframe .s_cover h1 span.o_animated_text",
        isCheck: true,
    },
    {
        content: "Click on the 'Animate Text' button",
        trigger: "div.o_we_animate_text",
    },
    {
        content: "Check that the animation was disabled for the title",
        trigger: "iframe .s_cover:not(:has(.o_animated_text))",
        isCheck: true,
    },
    {
        content: "Try to apply the text animation again",
        trigger: "div.o_we_animate_text",
    },
    {
        content: "Check that the animation was applied",
        trigger: "iframe .s_cover:has(span.o_animated_text)",
        isCheck: true,
    },
]);
