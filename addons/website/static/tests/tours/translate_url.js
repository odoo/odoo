/** @odoo-module */

import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

const translateUrl = function (newUrl) {
    return [{
        content: "Click on the 'Site' button",
        trigger: "button:contains('Site')",
        run: "click",
    }, {
        content: "Click on the 'Properties' button",
        trigger: "a:contains('Properties')",
        run: "click",
    }, {
        content: "Click on the input url",
        trigger: "[name=url] input.o_input",
        run: "click",
    }, {
        content: "Click on the translate button",
        trigger: "span.o_field_translate:contains('EN')",
        run: "click",
    }, {
        content: "Change the french translation of the contactus page url",
        trigger: `div.row:contains('French') input[type='text']`,
        // TODO: remove && click
        run: `edit ${newUrl} && click body`,
    }, {
        content: "Click on 'Save'",
        trigger: ".modal-content:contains('Translate: url') footer button:contains('Save')",
        run: "click",
    }, {
        content: "Click on 'Save and Close'",
        trigger: ".modal-content:contains('Page Properties') footer button:contains('Save & Close')",
        run: "click",
    }, {
        content: "Wait for the load operation to finish",
        trigger: "body.o_web_client:not(.modal-open)",
    }, {
        trigger: ":iframe .s_website_form",
    },
];
};

registerWebsitePreviewTour("translate_url_exists_in_other_language", {
    test: true,
    url: "/contactus",
}, () => [
    ...translateUrl("/page-en"),
]);

registerWebsitePreviewTour("translate_url_exists_in_same_language", {
    test: true,
    url: "/contactus",
}, () => [
    ...translateUrl("/page-fr"),
]);

registerWebsitePreviewTour("update_homepage_url", {
    test: true,
    url: "/contactus",
}, () => [
    ...translateUrl("/contactus-fr"),
]);

