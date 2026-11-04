import { clickOnSave, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "hide_sidebar_header",
    {
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Click on the header",
            trigger: ":iframe #o_main_nav",
            run: "click",
        },
        {
            content: "Click on header template",
            trigger: ".o_we_user_value_widget:has(we-title:contains(Template)) we-toggler",
            run: "click",
        },
        {
            content: "Change header template to 'Sidebar'",
            trigger: ".o_we_user_value_widget[title='Sidebar']",
            run: "click",
        },
        {
            content: "Ensure the header is 'Sidebar'",
            trigger: ":iframe #wrapwrap>header.o_header_sidebar",
            timeout: 10000,
        },
        {
            content: "Go to the theme tab",
            trigger: ".o_we_customize_theme_btn",
            run: "click",
        },
        {
            content: "Toggle 'Show Header' off",
            trigger: ".o_we_user_value_widget:has(we-title:contains(Show Header)) we-checkbox",
            run: "click",
        },
        {
            content: "Ensure the header has been hidden",
            trigger: ":iframe #wrapwrap:not(:has(:scope > header))",
            timeout: 10000,
        },
        {
            content: "Check that there's no header padding on the #wrapwrap",
            trigger: ":iframe #wrapwrap",
            run() {
                const style = getComputedStyle(this.anchor);
                if (style.paddingLeft !== "0px") {
                    throw new Error("There shouldn't be padding for the header");
                }
            },
        },
        ...clickOnSave(),
    ]
);
