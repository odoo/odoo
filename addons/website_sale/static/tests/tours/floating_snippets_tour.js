import { registry } from "@web/core/registry";
import {
    changeOptionInPopover,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    waitForEditMode,
} from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale.floating_snippets", {
    steps: () => [
        waitForEditMode,
        ...insertSnippet({
            id: "s_popup",
            name: "Popup",
            groupName: "Content",
        }),
        ...clickOnSnippet(".s_popup, .s_popup:not(:visible)"),
        ...changeOptionInPopover("Popup", "Show on", "All products"),
        ...clickOnSave(),
        {
            content: "Go to the shop page.",
            trigger: ":iframe a[href='/shop']",
            run: "click",
        },
        {
            content: "Open another product page.",
            trigger: ':iframe h6.o_wsale_products_item_title:contains("Floating Snippets Product B") a',
            run: "click",
        },
        {
            content: "Check that we navigated to another page.",
            trigger: ':iframe h1:contains("Floating Snippets Product B")',
        },
        {
            content: "Check that the popup is present on the other product page.",
            trigger: ":iframe .s_popup[data-show-on='allProducts']:not(:visible)",
        },
    ],
});
