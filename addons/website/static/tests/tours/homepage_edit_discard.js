/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour('homepage_edit_discard', {
    test: true,
    url: '/',
    edition: true,
}, () => [{
    trigger: ".o_we_discard_container button:not([disabled])",
    extra_trigger: "body:not(:has(.o_dialog))",
    content: "<b>Click Discard</b> to Discard all Changes.",
    position: "bottom",
}, {
    trigger: "iframe body:not(.editor_enable)",
    auto: true,
    run: () => null,
}]);
