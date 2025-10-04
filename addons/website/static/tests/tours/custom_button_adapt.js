/** @odoo-module */

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour(
    "custom_button_adapt",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        wTourUtils.dragNDrop({
            id: "s_button",
            name: "Button",
        }),
        {
            content: "Click on the button snippet",
            trigger: "iframe a.o_default_snippet_text:contains('Button')",
            run: "click",
        },
        {
            content: "Select button snippet animation option",
            trigger: ".snippet-option-WebsiteAnimate:nth-of-type(2) we-toggler",
            run: "click",
        },
        {
            content: "Select animation 'On Appearance' option",
            trigger: ".o_we_widget_opened [data-name='animation_on_appearance_opt']",
            run: "click",
        },
        {
            content: "Save the button snippet as custom snippet",
            trigger: ".snippet-option-SnippetSave:nth-of-type(1) we-button",
            run: "click",
        },
        {
            content: "Save the custom button snippet.",
            trigger: ".modal-content button:contains('Save and Reload')",
            run: "click",
        },
        {
            content: "Verify Custom button snippet has been saved",
            trigger: "#oe_snippets .oe_snippet[name='Custom Button']",
        },
        {
            content: "Drag the Custom Button and drop it near Contact us button",
            trigger:
                '#oe_snippets .oe_snippet[name="Custom Button"] .oe_snippet_thumbnail:not(.o_we_already_dragging)',
            extra_trigger: ".o_website_preview.editor_enable.editor_has_snippets",
            run: "drag_and_drop_native iframe [aria-label='Main'] [data-snippet='s_text_block'] .container",
        },
        {
            content: "Waiting for custom button to be rendered.",
            trigger:
                "iframe [aria-label='Main'] [data-snippet='s_text_block'] .container .o_animate_preview",
        },
        ...wTourUtils.clickOnSave(),
        {
            content:
                "Check that the custom button is NOT wrapped in <p> and did NOT copy style from sibling",
            trigger: "iframe [aria-label='Main'] .container .s_custom_snippet",
            run() {
                const customButton = this.$anchor[0];
                if (customButton.parentNode.tagName === "P") {
                    throw new Error(
                        "Custom button should not be wrapped in <p> when sibling button is present"
                    );
                }
            },
        },
    ]
);
