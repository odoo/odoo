import {
    assertCssVariable,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

let previousFooterViewId = null;
registerWebsitePreviewTour(
    "discard_rollback",
    {
        edition: true,
        url: "/",
    },
    () => [
        // Add a snippet: to have a change that doesn't directly save to backend
        ...insertSnippet({ id: "s_banner", name: "Banner", groupName: "Intro" }),
        {
            content: "Check that the snippet has been added",
            trigger: ":iframe #wrap section.s_banner",
        },
        // Header modifications
        {
            content: "Click on header",
            trigger: ":iframe header.o_header_standard",
            run: "click",
        },
        {
            content: "Change header scroll effect",
            trigger: "[data-class-action=o_header_fade_out]:not(:visible)",
            run: "click",
        },
        {
            trigger: ":iframe:not(:has(.o_loading_screen))",
        },
        {
            content: "Check that the header changed",
            trigger: ":iframe header.o_header_fade_out",
            run: "click",
        },
        // Call to action button modification (to test resetViewArch behavior)
        {
            content: "Click on call to action button",
            trigger: ":iframe .navbar a[href='/contactus']:contains('Test Rollback Button')",
            run: "click",
        },
        {
            content: "Disable call to action button",
            trigger:
                "[data-label=Actions] [data-action-param*='website.header_call_to_action'].active",
            run: "click",
        },
        {
            trigger: ":iframe:not(:has(.o_loading_screen))",
        },
        {
            content: "Check that the call to action button is not there anymore",
            trigger: ":iframe .navbar:not(:has(a[href='/contactus']))",
            run: "click",
        },
        // Footer modifications
        assertCssVariable("--footer-template", "default"),
        {
            content: "Save footer view id and click on it",
            trigger: ":iframe footer > #footer",
            run({ anchor }) {
                if (!anchor.dataset.oeId) {
                    throw Error("The footer doesn't have a template id");
                }
                previousFooterViewId = anchor.dataset.oeId;
                anchor.click();
            },
        },
        {
            content: "Change footer template",
            trigger: "[data-action-param*=template_footer_descriptive]:not(:visible)",
            run: "click",
        },
        {
            trigger: ":iframe:not(:has(.o_loading_screen))",
        },
        assertCssVariable("--footer-template", "descriptive"),
        {
            content: "Check that the footer changed",
            trigger: ":iframe footer > #footer",
            run({ anchor }) {
                if (!anchor.dataset.oeId) {
                    throw Error("The footer doesn't have a template id");
                }
                if (anchor.dataset.oeId === previousFooterViewId) {
                    throw Error("Footer view id didn't change");
                }
                previousFooterViewId = anchor.dataset.oeId;
            },
        },
        // Page layout modifications to trigger make_scss_customization
        {
            content: "Switch to theme tab",
            trigger: "#theme-tab",
            run: "click",
        },
        assertCssVariable("--layout", "full"),
        {
            content: "Change Page layout",
            trigger:
                "[data-action-id=customizeWebsiteVariable][data-action-value=postcard]:not(:visible)",
            run: "click",
        },
        {
            trigger: ":iframe:not(:has(.o_loading_screen))",
        },
        assertCssVariable("--layout", "postcard"),
        // Discard
        {
            content: "Click on discard",
            trigger: ".o-snippets-top-actions [data-action='cancel']",
            run: "click",
        },
        {
            content: "Confirm dialog",
            trigger: `.modal-content footer .btn-primary`,
            run: "click",
        },
        {
            trigger: ":iframe:not(:has(.o_loading_screen))",
        },
        // Check that everything has been correctly discarded
        {
            content: "The snippet should not be there",
            trigger: ":iframe #wrap:not(:has(section.s_banner))",
        },
        {
            content: "Check that the header rollbacked",
            trigger: ":iframe header.o_header_standard",
        },
        {
            content: "Check that call to action is there with the correct text",
            trigger: ":iframe .navbar a[href='/contactus']:contains('Test Rollback Button')",
        },
        assertCssVariable("--footer-template", "default"),
        {
            content: "Check that the footer rollbacked",
            trigger: ":iframe footer > #footer",
            run({ anchor }) {
                if (anchor.dataset.oeId === previousFooterViewId) {
                    throw Error("The footer didn't rollback");
                }
            },
        },
        {
            ...assertCssVariable("--layout", "full"),
            content: "Check that Page layout rollbacked",
        },
    ]
);
