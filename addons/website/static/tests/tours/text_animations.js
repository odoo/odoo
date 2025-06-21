/** @odoo-module */

import {
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("text_animations", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: "s_cover",
        name: "Cover",
        groupName: "Intro",
    }),
    {
        content: "Click on the snippet title",
        trigger: ":iframe .s_cover h1",
        run: "dblclick", // Make sure the title is selected.
    },
    {
        content: "Click on the 'Animate Text' button to activate the option",
        trigger: "div.o_we_animate_text",
        run: "click",
    },
    {
        content: "Check that the animation was applied",
        trigger: ":iframe .s_cover h1 span.o_animated_text",
    },
    {
        content: "Click on the 'Animate Text' button",
        trigger: "div.o_we_animate_text",
        run: "click",
    },
    {
        content: "Check that the animation was disabled for the title",
        trigger: ":iframe .s_cover:not(:has(.o_animated_text))",
    },
    {
        content: "Open the text background color colorpicker",
        trigger: "button#oe-fore-color",
        run: "click",
    },
    {
        content: "Add a background color on the selected text",
        trigger: ".o_colorpicker_section [data-color='black']",
        run: "click",
    },
    {
        content: "Try to apply the text animation again",
        trigger: "div.o_we_animate_text",
        run: "click",
    },
    {
        content: "Check that the animation was applied and that the <font> element is inside the o_animated_text element",
        trigger: ":iframe .s_cover:has(span.o_animated_text > font.bg-black)",
    },
]);
