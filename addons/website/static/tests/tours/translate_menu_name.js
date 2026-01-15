import {
    clickOnExtraMenuItem,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
import { stepUtils } from "@web_tour/tour_utils";
import { translationIsReady } from "@web/core/l10n/translation";

registerWebsitePreviewTour(
    "translate_menu_name",
    {
        url: "/pa_GB",
        edition: false,
    },
    () => [
        {
            content: "Open Edit dropdown",
            trigger: ".o_menu_systray button:contains('Edit')",
            run: "click",
        },
        {
            content: "activate translate mode",
            trigger: ".o_translate_website_dropdown_item",
            run: "click",
        },
        {
            content: "Close the dialog",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        clickOnExtraMenuItem({}, true),
        {
            content: "translate the menu entry",
            trigger: ':iframe a[href="/englishURL"] span',
            run: "editor value pa-GB",
        },
        ...clickOnSave(),
        {
            content: "Back to preview mode",
            trigger: ".o_edit_website_container button",
        },
        {
            trigger: "body:not(.o_builder_open)",
            noPrepend: true,
        },
        stepUtils.waitIframeIsReady(),
        {
            content: "Await translationIsReady",
            trigger: "body",
            run: async () => {
                await translationIsReady;
            },
        },
    ]
);
