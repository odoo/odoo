import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("shop_editor", {
    url: "/shop",
    edition: true,
}, () => [{
    content: "Click on pricelist dropdown",
    trigger: ":iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown]",
    run: "click",
},
{
    trigger: ":iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown][aria-expanded=true]",
},
{
    trigger: ":iframe input[name=search]",
    content: "Click somewhere else in the shop.",
    run: "click",
},
{
    trigger: ":iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown][aria-expanded=false]",
},
{
    trigger: ":iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown]",
    content: "Click on the pricelist again.",
    run: "click",
}, {
    trigger: ":iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown][aria-expanded=true]",
    content: "Check pricelist dropdown opened",
}]);

registerWebsitePreviewTour("shop_editor_set_product_ribbon", {
    url: "/shop",
    edition: true,
}, () => [{
    content: "Click on first product",
    trigger: ":iframe .oe_product:first",
    run: "click",
}, {
    content: "Open the ribbon selector",
    trigger: ".o_wsale_ribbon_select + button:contains('None')",
    run: "click",
}, {
    content: "Select a ribbon",
    trigger: ".o_popover div.o-dropdown-item:contains('Sale')",
    run: "click",
},
...clickOnSave(),
{
    content: "Check that the ribbon was properly saved",
    trigger: ':iframe .oe_product:first .o_ribbons:contains("Sale")',
}]);

registerWebsitePreviewTour("shop_editor_no_alternative_products_visibility_tour", {
    url: "/shop",
    edition: false,
}, () => [
    {
        content: "Select the product with alternative products",
        trigger: ':iframe .oe_product_cart[aria-label="product_with_alternative"] a',
        run: "click",
    },
    {
        content: "Ensure product page is loaded before clicking on Edit",
        trigger: ':iframe #product_details',
    },
    ...clickOnEditAndWaitEditMode(),
    {
        trigger: ':iframe .s_dynamic_snippet_title h4',
        run: "click",
    },
    {
        content: "Edit the alternative products section header",
        trigger: `:iframe .container[contenteditable="true"] h4`,
        run: function () {
            this.anchor.textContent = "Edited Alternative"
            this.anchor.dispatchEvent(new Event("input", { bubbles: true }));
        },
    },
    ...clickOnSave(),
    {
        content: "Navigate back to shop page",
        trigger: ':iframe .breadcrumb-item a',
        run: "click",
    },
    {
        content: "Select the product without alternative products",
        trigger: ':iframe .oe_product_cart[aria-label="product_without_alternative"] a',
        run: "click",
    },
    {
        content: "Ensure alternative products section is hidden",
        trigger: ':iframe .s_dynamic_snippet_products:not(:visible)',
    }
]);
