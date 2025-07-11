import { clickOnSave, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

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
