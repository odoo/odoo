/** @odoo-module */

import wTourUtils from "@website/js/tours/tour_utils";

const translateUrl = function (newUrl, language) {
    return [{
        content: "Click on the 'Site' button",
        trigger: "button:contains('Site')",
    }, {
        content: "Click on the 'Properties' button",
        trigger: "a:contains('Properties')",
    },
    {
        content: "Click on the translate button",
        trigger: "span.o_field_translate:contains('EN')",
    }, {
        content: "Change the translation of the contactus page url",
        trigger: `div.row:contains(${language}) input[type='text']`,
        // TODO: remove && click
        run: `edit ${newUrl} && click body`,
    }, {
        content: "Click on 'Save'",
        trigger: ".modal-content:contains('Translate: url') footer button:contains('Save')",
    },
    {
        content: "Click on 'Save and Close'",
        trigger: ".modal-content:contains('Page Properties') footer button:contains('Save & Close')",
    },
    {
        content: "Wait for the load operation to finish",
        trigger: "body.o_web_client:not(.modal-open)",
        extra_trigger: ":iframe .s_website_form",
        isCheck: true,
    },
];
}

wTourUtils.registerWebsitePreviewTour("translate_url_exists_in_other_language", {
    test: true,
    url: "/contactus",
}, () => [
    ...translateUrl("/page-en", "French"),
]);

wTourUtils.registerWebsitePreviewTour("translate_url_exists_in_same_language", {
    test: true,
    url: "/contactus",
}, () => [
    ...translateUrl("/page-fr", "French"),
]);

wTourUtils.registerWebsitePreviewTour("update_homepage_url", {
    test: true,
    url: "/contactus",
}, () => [
    ...translateUrl("/contactus-en", "English"),
]);

