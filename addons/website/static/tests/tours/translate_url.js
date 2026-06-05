import { addLanguage, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

const enterPageProperties = [
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
];

const enterPagePropertiesAndClickOnInputUrl = [
    ...enterPageProperties,
    {
        content: "Click on the input url",
        trigger: "[name=url] input.o_input",
        run: "click",
    },
];

const saveChanges = [
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

const translateUrl = function (newUrl) {
    return [
        ...enterPagePropertiesAndClickOnInputUrl,
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
    ];
};

registerWebsitePreviewTour("translate_url_exists_in_other_language", {}, () => [
    ...translateUrl("/page-en"),
    ...saveChanges,
]);

registerWebsitePreviewTour("translate_url_exists_in_same_language", {}, () => [
    ...translateUrl("/page-fr"),
    ...saveChanges,
]);

registerWebsitePreviewTour("update_homepage_url", {}, () => [
    ...translateUrl("/contactus-fr"),
    ...saveChanges,
]);

registerWebsitePreviewTour("set_homepage_property_of_a_page", {}, () => [
    ...enterPageProperties,
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

registerWebsitePreviewTour("add_language_and_translate_url", { edition: true }, () => [
    ...addLanguage("Parseltongue", "pa-GB"),
    ...enterPagePropertiesAndClickOnInputUrl,
    {
        content: "Check that the translate button is visible",
        trigger: "button.o_field_translate:contains('EN')",
    },
]);

registerWebsitePreviewTour("translate_url_and_redirect", {}, () => [
    ...translateUrl("/contactus-fr"),
    {
        content: "Click on 'Redirect Old URL'",
        trigger: ".modal-content:contains('Page Properties') #redirect_old_url_0",
        run: "click",
    },
    ...saveChanges,
]);
