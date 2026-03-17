import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

const translateUrl = function (newUrl) {
    return [
        {
            content: "Click on the 'Site' button",
            trigger: "button:contains('Site')",
            run: "click",
        },
        {
            content: "Click on the 'Properties' button",
            trigger: "a:contains('Properties')",
            run: "click",
        },
        {
            content: "Click on the input url",
            trigger: "[name=url] input.o_input",
            run: "click",
        },
        {
            content: "Click on the translate button",
            trigger: "button.o_field_translate:contains('EN')",
            run: "click",
        },
        {
            content: "Change the french translation of the contactus page url",
            trigger: `div.row:contains('French') input[type='text']`,
            run: `edit ${newUrl}`,
        },
        {
            content: "Click on 'Save' in the translate modal",
            trigger: ".modal-content:contains('Translate: url') footer button:contains('Save')",
            run: "click",
        },
        {
            content: "Click on the 'Save' of the Page Properties",
            trigger: ".modal-content:contains('Page Properties') footer button:contains('Save')",
            run: "click",
        },
        {
            content: "Wait for the load operation to finish",
            trigger: "body.o_web_client:not(.modal-open)",
        },
        {
            trigger: ":iframe .s_website_form",
        },
    ];
};

registerWebsitePreviewTour("translate_url_exists_in_other_language", {}, () => [
    ...translateUrl("/page-en"),
]);

registerWebsitePreviewTour("translate_url_exists_in_same_language", {}, () => [
    ...translateUrl("/page-fr"),
]);

registerWebsitePreviewTour("update_homepage_url", {}, () => [...translateUrl("/contactus-fr")]);

registerWebsitePreviewTour("set_homepage_property_of_a_page", {}, () => [
    {
        content: "Click on the 'Site' button",
        trigger: "button:contains('Site')",
        run: "click",
    },
    {
        content: "Click on the 'Properties' button",
        trigger: "a:contains('Properties')",
        run: "click",
    },
    {
        content: "Click on the 'Is Homepage' button",
        trigger: "#is_homepage_0",
        run: "click",
    },
    {
        content: "Click on the 'Save' of the Page Properties",
        trigger: ".modal-content:contains('Page Properties') footer button:contains('Save')",
        run: "click",
    },
    {
        content: "Wait for the load operation to finish",
        trigger: "body.o_web_client:not(.modal-open)",
    },
]);
