import {
    insertSnippet,
    registerWebsitePreviewTour,
    clickOnSave,
    goBackToBlocks,
    clickToolbarButton,
} from "@website/js/tours/tour_utils";
import { browser } from "@web/core/browser/browser";

function checkAccordionItemExpanded() {
    return [
        {
            content: "Check that the accordion item's content is visible",
            trigger: ":iframe .s_accordion .accordion-item:first-child .accordion-collapse.show",
        },
    ];
}

registerWebsitePreviewTour(
    "anchor_behaviour_on_accordion_same_tab",
    {
        edition: true,
        url: "/",
    },
    () => [
        ...insertSnippet({
            id: "s_accordion",
            name: "Accordion",
        }),
        {
            content: "Click the first accordion item to select it",
            trigger: ":iframe .s_accordion .accordion-item:first-child",
            run: "click",
        },
        {
            content: "Create anchor for this accordion item",
            trigger: "[data-container-title='Accordion Item'] .oe_snippet_anchor",
            async run(helpers) {
                // Patch and ignore write on clipboard in tour as we don't have permissions
                browser.navigator.clipboard.writeText = () => {
                    console.info("Copy in clipboard ignored!");
                };
                await helpers.click();
            },
        },
        goBackToBlocks(),
        ...insertSnippet({
            id: "s_text_block",
            name: "Text",
            groupName: "Text",
        }),
        {
            content: "Click inside the first paragraph of text block",
            trigger: ":iframe .s_text_block .container p:first-child",
            run: "editor Paragraph",
        },
        ...clickToolbarButton("Paragraph", "#wrap .s_text_block p", "Add a link", false),
        {
            content: "Type the link URL",
            trigger: ".o-we-linkpopover .o_we_href_input_link",
            run: "edit /#What-services-does-your-company-offer-%3F",
        },
        {
            content: "Apply the link",
            trigger: ".o-we-linkpopover .o_we_apply_link",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Click the newly created link in text block",
            trigger:
                ':iframe .s_text_block .container p:first-child a[href="/#What-services-does-your-company-offer-%3F"]',
            run: "click",
        },
        ...checkAccordionItemExpanded(),
    ]
);

registerWebsitePreviewTour(
    "anchor_behaviour_on_accordion_new_tab",
    {
        url: "/#What-services-does-your-company-offer-%3F",
    },
    () => [...checkAccordionItemExpanded()]
);
