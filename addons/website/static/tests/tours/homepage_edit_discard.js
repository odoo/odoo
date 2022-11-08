/** @odoo-module **/

import wTourUtils from "website.tour_utils";

wTourUtils.registerWebsitePreviewTour('homepage_edit_discard', {
    test: true,
    url: '/',
    edition: true,
}, [{
    trigger: "#oe_snippets button[data-action=\"cancel\"]:not([disabled])",
    extra_trigger: "body:not(:has(.o_dialog))",
    content: "<b>Click Discard</b> to Discard all Changes.",
    position: "bottom",
}, {
    trigger: "iframe body:not(.editor_enable)",
    auto: true,
    run: () => null,
}]);
