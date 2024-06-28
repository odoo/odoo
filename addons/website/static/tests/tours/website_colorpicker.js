/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";
const TARGET_BODY_DATA_COLOR = "linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)";
wTourUtils.registerWebsitePreviewTour(
    "custom_gradient_on_contactus_button",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Click the 'Contact Us' button in the navigation bar",
            trigger: "iframe .o_main_nav a.btn-primary[href='/contactus']",
        },
        {
            content: "Click on 'Edit Link' to customize the button",
            trigger: "iframe .o_edit_menu_popover .o_we_edit_link",
        },
        {
            content: "Open the foreground colorpicker",
            trigger: "#toolbar:not(.oe-floating) #oe-text-color",
        },
        {
            content: "Go to the 'Gradient' tab",
            trigger: ".o_we_colorpicker_switch_pane_btn[data-target='gradients']",
        },
        {
            content: "Click on the custom button to apply a custom gradient",
            trigger: ".o_custom_gradient_btn",
        },
        {
            content: "Trigger the mouseleave event on the 'Custom' button",
            trigger: ".o_custom_gradient_btn",
            run() {
                this.$anchor.trigger("mouseleave");
            },
        },
        {
            content: "Check if font tag is applied to 'Contact Us'",
            trigger: "iframe .o_main_nav a.btn-primary[href='/contactus'] font:contains('Contact Us')",
            run: () => {}, // It's a check.
        },
        {
            content: "Trigger 'mouseenter' and 'mouseleave' on selected gradient",
            trigger: `.o_we_color_btn[data-color='${TARGET_BODY_DATA_COLOR}'].selected`,
            run() {
                this.$anchor.trigger("mouseenter");
                this.$anchor.trigger("mouseleave");
            },
        },
        {
            content: "Check if font tag is applied to 'Contact Us' after hovering on selected gradient",
            trigger: "iframe .o_main_nav a.btn-primary[href='/contactus'] font:contains('Contact Us')",
            run: () => {}, // It's a check.
        },
        {
            content: "Trigger 'mouseenter' and 'mouseleave' on linear-gradient",
            trigger: ".colorpicker we-button[data-gradient-type='linear-gradient'].active",
            run() {
                this.$anchor.trigger("mouseeenter");
                this.$anchor.trigger("mouseleave");
            },
        },
        {
            content: "Check if font tag is applied to 'Contact Us' after hovering on linear-gradient",
            trigger: "iframe .o_main_nav a.btn-primary[href='/contactus'] font:contains('Contact Us')",
            run: () => {}, // It's a check.
        },
    ]
);
