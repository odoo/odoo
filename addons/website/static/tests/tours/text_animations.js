import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickToolbarButton,
    openEffectsPanelSection,
} from "@website/js/tours/tour_utils";

function openAnimationChoices() {
    return [
        ...clickToolbarButton("snippet title", ".s_cover h1", "Text effects", true),
        ...openEffectsPanelSection("animateText"),
        {
            content: "Open the animation choices",
            trigger: ".o_animate_text_section [data-label='Animation'] .o_hb_select_toggle",
            run: "click",
        },
    ];
}

function setTextAnimation(trigger, value) {
    return [
        ...openAnimationChoices(),
        {
            content: "Animate the text on appearance",
            trigger: ".o-dropdown--menu .o-dropdown-item:contains('On Appearance')",
            run: "click",
        },
        {
            content: "Open the effect choices",
            trigger: ".o_animate_text_section [data-label='Effect'] .o_hb_select_toggle",
            run: "click",
        },
        {
            content: "Select the text animation",
            trigger: `.o-dropdown--menu [data-action-value="${value}"]`,
            run: "click",
        },
        {
            content: "Click away to close the panel",
            trigger: `${trigger}:not(.o_popover)`,
            run: "click",
        },
    ];
}

registerWebsitePreviewTour(
    "text_animations",
    {
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
        ...openAnimationChoices(),
        {
            content: "Remove the text animation",
            trigger: ".o-dropdown--menu .o-dropdown-item:contains('None')",
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
