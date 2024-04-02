/** @odoo-module **/

import wTourUtils from "website.tour_utils";

// TODO remove this test; it is badly written: you just have to change the fact
// that editor_enable is added on the body to silently make it useless +
// useless extra_trigger + useless auto: true + ... A better duplicate of it has
// been made with "website_no_dirty_page".
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
