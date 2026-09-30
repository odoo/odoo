import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickToolbarButton,
} from "@website/js/tours/tour_utils";

function setTextAnimation(trigger, value) {
    return [
        ...clickToolbarButton("snippet title", ".s_cover h1", "Animate Text", true),
        {
            content: "Open Effect options in the popover",
            trigger: ".o_popover [data-label='Effect'] button.dropdown-toggle",
            run: "click",
        },
        {
            content: "Select the text animation",
            trigger: `.o_popover [data-action-value="${value}"]`,
            run: "click",
        },
        {
            content: "Click away to close the popover",
            trigger: `${trigger}:not(.o_popover)`,
            run: "click",
        },
    ];
}

registerWebsitePreviewTour(
    "text_animations",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_cover",
            name: "Cover",
            groupName: "Intro",
        }),
        ...setTextAnimation(":iframe .s_cover h1", "o_anim_slide_in"),
        {
            content: "Check that the animation was applied",
            trigger: ":iframe .s_cover .o_animated_text",
        },
        ...clickToolbarButton("snippet title", ".s_cover h1", "Animate Text", true),
        {
            content: "Reset the text animation",
            trigger: ".o_popover button[title='Reset']",
            run: "click",
        },
        {
            content: "Check that the animation was disabled for the title",
            trigger: ":iframe .s_cover:not(:has(.o_animated_text))",
        },
        ...setTextAnimation(":iframe .s_cover h1", "o_anim_slide_in"),
        {
            content: "Check that the animation was applied",
            trigger: ":iframe .s_cover:has(span.o_animated_text)",
        },
    ]
);
