/** @odoo-module **/

import wTourUtils from "website.tour_utils";

wTourUtils.registerWebsitePreviewTour("shop_editor", {
    test: true,
    url: "/shop",
    edition: true,
}, [{
    content: "Click on pricelist dropdown",
    trigger: "iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown]",
}, {
    trigger: "iframe input[name=search]",
    extra_trigger: "iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown][aria-expanded=true]",
    content: "Click somewhere else in the shop.",
}, {
    trigger: "iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown]",
    extra_trigger: "iframe div.o_pricelist_dropdown a[data-bs-toggle=dropdown][aria-expanded=false]",
    content: "Click on the pricelist again.",
}]);
