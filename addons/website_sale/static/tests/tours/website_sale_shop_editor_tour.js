/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("shop_editor", {
    test: true,
    url: "/shop",
    edition: true,
}, () => [{
    content: "Click on pricelist dropdown",
    trigger: ":iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown]",
    run: "click",
}, {
    trigger: ":iframe input[name=search]",
    extra_trigger: ":iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown][aria-expanded=true]",
    content: "Click somewhere else in the shop.",
    run: "click",
}, {
    trigger: ":iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown]",
    extra_trigger: ":iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown][aria-expanded=false]",
    content: "Click on the pricelist again.",
    run: "click",
}, {
    trigger: ":iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown][aria-expanded=true]",
    content: "Check pricelist dropdown opened",
    isCheck: true,
}]);

wTourUtils.registerWebsitePreviewTour("shop_editor_set_product_ribbon", {
    test: true,
    url: "/shop",
    edition: true,
}, () => [{
    content: "Click on first product",
    trigger: ":iframe .oe_product:first",
    run: "click",
}, {
    content: "Open the ribbon selector",
    trigger: ".o_wsale_ribbon_select we-toggler",
    run: "click",
}, {
    content: "Select a ribbon",
    trigger: '.o_wsale_ribbon_select we-button:contains("Sale")',
    run: "click",
},
...wTourUtils.clickOnSave(),
{
    content: "Check that the ribbon was properly saved",
    trigger: ':iframe .oe_product:first .o_ribbon:contains("Sale")',
    isCheck: true,
}]);
