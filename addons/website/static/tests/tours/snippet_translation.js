import { localization } from "@web/core/l10n/localization";
import { translatedTermsGlobal } from "@web/core/l10n/translation";
import {
    clickOnEditAndWaitEditMode,
    clickOnEditAndWaitEditModeInTranslatedPage,
    clickOnSave,
    getClientActionUrl,
    insertSnippet,
    registerWebsitePreviewTour,
    testSwitchWebsite,
} from "@website/js/tours/tour_utils";
import { stepUtils } from "@web_tour/tour_utils";
import { registry } from "@web/core/registry";

registerWebsitePreviewTour("snippet_translation", {}, () => [
    stepUtils.goToUrl(getClientActionUrl()),
    {
        content: "Wait for website preview and check language",
        trigger: ":iframe html:has(body:contains(welcome to your)):has(.o_top_fixed_element)",
        run: () => {
            if (localization.code !== "fu_GB") {
                console.error("the user language is not properly set");
            } else {
                translatedTermsGlobal["Save"] = "Save in fu_GB";
            }
        },
    },
    ...clickOnEditAndWaitEditMode(),
    ...insertSnippet({ id: "s_cover", name: "Cover", groupName: "Intro" }),
    {
        content: "Check that contact us contain Parseltongue",
        trigger: ':iframe .s_cover .btn-outline-secondary:contains("Contact us in Parseltongue")',
    },
    {
        content: "Check that the save button contains 'in fu_GB'",
        trigger: '.btn[data-action="save"]:contains("Save in fu_GB")',
    },
]);

const switchTo = (lang) => [
    {
        content: `Switch to ${lang}`,
        trigger: `:iframe .js_change_lang[data-url_code='${lang}']`,
        // After clicking a language link, the iframe navigates to a new document.
        // We must wait for the old contentDocument to be replaced and the new
        // one to be fully loaded before proceeding, otherwise the next steps
        // may run against the old (unloading) or partially loaded document.
        async run({ anchor, click }) {
            const iframe = anchor.ownerDocument.defaultView.frameElement;
            const oldDoc = iframe.contentDocument;
            await click(anchor);
            while (!iframe.contentDocument || iframe.contentDocument === oldDoc) {
                await new Promise((r) => setTimeout(r, 50));
            }
            while (iframe.contentDocument.readyState !== "complete") {
                await new Promise((r) => setTimeout(r, 50));
            }
        },
    },
    {
        content: `Wait until ${lang} is applied`,
        trigger: `:iframe html[lang*="${lang}"]`,
    },
];

registry.category("web_tour.tours").add("snippet_translation_changing_lang", {
    steps: () => [
        stepUtils.goToUrl(getClientActionUrl()),
        stepUtils.waitIframeIsReady(),
        {
            content: "Open dropdown language selector",
            trigger: ":iframe .js_language_selector button",
            run: "click",
        },
        ...switchTo("pa_GB"),
        {
            content: "Open dropdown language selector",
            trigger: ":iframe .js_language_selector button",
            run: "click",
        },
        ...switchTo("en"),
        {
            content: "Open Edit dropdown",
            trigger: ".o_edit_website_container button",
            run: "click",
        },
        {
            content: "Enable translation",
            trigger: ".o_translate_website_dropdown_item",
            run: "click",
        },
        {
            content: "Close the dialog",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        ...clickOnSave(),
        ...clickOnEditAndWaitEditModeInTranslatedPage(),
        ...insertSnippet({ name: "Cover", id: "s_cover", groupName: "Intro" }),
        {
            content: "Check that contact us contain Parseltongue",
            trigger:
                ':iframe .s_cover .btn-outline-secondary:contains("Contact us in Parseltongue")',
        },
    ],
});

registerWebsitePreviewTour("snippet_translation_switching_website", {}, () => [
    stepUtils.goToUrl(getClientActionUrl()),
    ...clickOnEditAndWaitEditModeInTranslatedPage(),
    ...insertSnippet({ id: "s_cover", name: "Cover", groupName: "Intro" }),
    {
        content: "Check that contact us contain Parseltongue",
        trigger: ":iframe .s_cover .btn-outline-secondary:contains('Contact us in Parseltongue')",
    },
    ...clickOnSave(),
    ...testSwitchWebsite("website fu_GB"),
    ...clickOnEditAndWaitEditMode(),
    ...insertSnippet({ id: "s_cover", name: "Cover", groupName: "Intro" }),
    {
        content: "Check that contact us contain Fake User Lang",
        trigger: ":iframe .s_cover .btn-outline-secondary:contains('Fake User Lang')",
    },
]);
registerWebsitePreviewTour("snippet_dialog_rtl", {}, () => [
    stepUtils.goToUrl(getClientActionUrl()),
    ...clickOnEditAndWaitEditMode(),
    {
        trigger: ".o_builder_sidebar_open",
    },
    {
        content: "Select a category snippet to show the snippet dialog",
        trigger: `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name="Intro"].o_draggable .o_snippet_thumbnail_area`,
        run: "click",
    },
    {
        content: "Check that the snippets preview is in rtl",
        trigger: ":iframe .o_snippets_preview_row[dir=rtl]",
    },
    {
        content: "Check that web.assets_frontend CSS bundle is in rtl",
        trigger: ":iframe link[type='text/css'][href*='/web.assets_frontend.rtl']:not(:visible)",
    },
]);
