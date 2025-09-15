import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
import { stepUtils } from "@web_tour/tour_utils";
import { translationIsReady } from "@web/core/l10n/translation";

function createNewPage() {
    return [
        {
            content: "Open +New content",
            trigger: ".o_menu_systray .o_menu_systray_item.o_new_content_container button",
            run: "click",
        },
        {
            content: "Create a New page",
            trigger: `button.o_new_content_element img[src="/website/static/description/icon.png"]`,
            run: "click",
        },
        {
            content: "Select Blank page",
            trigger: ".o_page_template:has(div.text-muted) .o_button_area:not(:visible)",
            run: "click",
        },
        {
            content: "Page name",
            trigger: ".modal-dialog .o_website_dialog input",
            run: "edit Test",
        },
        {
            content: "Confirm creation",
            trigger: ".modal-dialog .o_website_dialog .btn-primary",
            run: "click",
        },
        {
            trigger: ".o_builder_sidebar_open",
            timeout: 20000,
        },
        ...insertSnippet({
            id: "s_banner",
            name: "Banner",
            groupName: "Intro",
        }),
        {
            content: "Click on the link",
            trigger: ":iframe main section.s_banner a",
            async run(helpers) {
                await helpers.click();
                const el = this.anchor;
                const sel = el.ownerDocument.getSelection();
                sel.collapse(el, 0);
                el.focus();
            },
        },
        {
            content: "Click on Edit link",
            trigger: ".o_we_edit_link",
            run: "click",
        },
        {
            content: "Replace URL",
            trigger: ".o-we-linkpopover .o_we_href_input_link",
            run: "edit /test_view",
        },
        {
            content: "Apply",
            trigger: ".o-we-linkpopover .btn-primary",
            run: "click",
        },
        ...clickOnSave("bottom", 50000, false),
    ];
}

function openHtmlEditor() {
    return [
        {
            content: "Open Site menu",
            trigger: ".o_menu_sections [data-menu-xmlid='website.menu_site']",
            run: "click",
        },
        {
            content: "Open HTML editor",
            trigger: ".o-overlay-item .dropdown-item[data-menu-xmlid='website.menu_ace_editor']",
            run: "click",
        },
        {
            content: "Edit anyway",
            trigger: ".o_resource_editor_wrapper [role='alert'] button.btn-link",
            run: "click",
        },
    ];
}

function saveHtmlEditor() {
    return [
        {
            content: "Save the html editor",
            trigger: ".o_resource_editor button.btn-primary",
            run: "click",
        },
        {
            content: "Close the html editor",
            trigger: ".o_resource_editor button.btn-secondary",
            run: "click",
        },
    ];
}

function singleLanguage() {
    return [
        {
            content: "Ensure single language site",
            trigger: ":iframe body:not(:has(.js_language_selector))",
        },
        // new page
        ...createNewPage(),
        ...openHtmlEditor(),
        {
            content: "Change text",
            trigger: 'div.ace_line .ace_xml:contains("oe_structure")',
            run() {
                window.ace.edit(document.querySelector("#resource-editor div"))
                    .getSession()
                    .insert({row: 8, column: 1}, '<p>More text</p>\n');
            },
        },
        ...saveHtmlEditor(),
        {
            content: "Ensure page is updated",
            trigger: ":iframe body:contains(More text)",
        },
        // xml record
        {
            content: "Go to test_view page",
            trigger: ":iframe main section.s_banner a",
            run: "click",
        },
        {
            content: "Wait until page is reached",
            trigger: ":iframe body:contains(Test View)",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Edit template text",
            trigger: ":iframe main p.o_editable[data-oe-field='arch'][contenteditable='true']",
            run: "editor Modified Text",
        },
        ...clickOnSave("bottom", 50000, false),
        ...openHtmlEditor(),
        {
            content: "Change text",
            trigger: 'div.ace_line .ace_xml:contains("test_website.test_view")',
            run() {
                window.ace.edit(document.querySelector("#resource-editor div"))
                   .getSession()
                   .insert({row: 2, column: 36}, 'Further ');
            },
        },
        ...saveHtmlEditor(),
        {
            content: "Ensure view is updated",
            trigger: ":iframe body:contains(Further Modified Text)",
        },
    ];
}

const ensureFrUser = {
    content: "Ensure FR user",
    trigger: ".o_website_systray:contains(Publié)",
};

const ensureEnUser = {
    content: "Ensure EN user",
    trigger: ".o_website_systray:contains(Published)",
};

const ensureFrSite = {
    content: "Ensure FR site",
    trigger: ":iframe .o_main_nav:contains(Accueil)",
};

const ensureEnSite = {
    content: "Ensure EN site",
    trigger: ":iframe .o_main_nav:contains(Home)",
};

registerWebsitePreviewTour(
    "translation_single_language_fr_user_fr_site",
    {
        url: "/",
    },
    () => [
        ensureFrUser,
        ensureFrSite,
        ...singleLanguage(),
    ]
);

registerWebsitePreviewTour(
    "translation_single_language_en_user_fr_site",
    {
        url: "/",
    },
    () => [
        ensureEnUser,
        ensureFrSite,
        ...singleLanguage(),
    ]
);

registerWebsitePreviewTour(
    "translation_single_language_fr_user_en_site",
    {
        url: "/",
    },
    () => [
        ensureFrUser,
        ensureEnSite,
        ...singleLanguage(),
    ]
);

function switchLanguage(lang, timeout = 50000) {
    return [
        {
            content: "Ensure was in other language",
            trigger: `:iframe .o_header_language_selector:contains(${lang !== "fr" ? "Français" : "English"})`,
            timeout,
        }, {
            content: "Open language dropdown",
            trigger: ":iframe .o_header_language_selector .dropdown-toggle",
            run: "click",
        }, {
            content: "Select language",
            trigger: `:iframe .o_header_language_selector .js_change_lang[data-url_code=${lang}]`,
            run: "click",
        }, {
            content: "Wait until target page is loaded",
            trigger: `:iframe .o_header_language_selector:contains(${lang === "fr" ? "Français" : "English"})`,
            timeout,
        }
    ];
}

// TODO Such a step should not be needed, but test randomly fails without it.
const awaitTranslationIsReady = {
    content: "Await translationIsReady",
    trigger: "body",
    run: async () => {
        await translationIsReady;
    },
};

function openTranslate(timeout = 50000) {
    return [
        stepUtils.waitIframeIsReady(),
        awaitTranslationIsReady,
        {
            content: "Open edit dropdown",
            trigger: ".o_edit_website_container button",
            run: "click",
        }, {
            content: "Enter translate mode",
            trigger: ".o_translate_website_dropdown_item",
            run: "click",
        }, {
            content: "Effect's 200ms setTimeout passed",
            trigger: ".o_builder_open .o_main_navbar.d-none:not(:visible)",
        }, {
            content: "Translatable text became highlighted",
            trigger: ":iframe [data-oe-translation-state=to_translate]",
            timeout,
        }, {
            content: "Confirm popup",
            trigger: ".o_website_dialog .btn-secondary",
            run: "click",
        }
    ];
}

function saveTranslation(timeout = 50000) {
    return [
        {
            content: "Save translation",
            trigger: ".o-website-builder_sidebar button[data-action=save]",
            run: "click",
        }, {
            content: "Back to preview mode",
            trigger: ".o_edit_website_container button",
            timeout,
        }, {
            trigger: "body:not(.o_builder_open)",
            noPrepend: true,
            timeout,
        },
        stepUtils.waitIframeIsReady(),
        awaitTranslationIsReady,
    ];
}

function multiLanguage(mainLanguage, secondLanguage) {
    return [
        {
            content: "Ensure multi language site",
            trigger: ":iframe body:has(.js_language_selector)",
        },
        // new page
        ...createNewPage(),
        ...switchLanguage(secondLanguage),
        ...openTranslate(),
        {
            content: "Translate some text",
            trigger: ":iframe h1 [data-oe-translation-state=to_translate]",
            run: "editor Some translated text",
        },
        ...saveTranslation(),
        {
            content: "Check translation is displayed",
            trigger: ":iframe h1:contains(Some translated text)",
        },
        ...openHtmlEditor(),
        {
            content: "Change text",
            trigger: 'div.ace_line .ace_xml:contains("oe_structure")',
            run() {
                window.ace.edit(document.querySelector("#resource-editor div"))
                    .getSession()
                    .insert({row: 6, column: 50}, "more text ");
            },
        },
        {
            content: "Pollute old DOM to detect reload",
            trigger: ":iframe body",
            run() {
                this.anchor.dataset.reloaded = false;
            },
        },
        ...saveHtmlEditor(),
        {
            content: "Ensure page is NOT updated",
            trigger: ":iframe body:not([data-reloaded=false]) h1:not(:contains(more text))",
        },
        ...switchLanguage(mainLanguage),
        {
            content: "Ensure French page IS updated",
            trigger: ":iframe h1:contains(more text)",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Change text again",
            trigger: ":iframe h1",
            run: "editor Yet another version of the text.",
        },
        ...clickOnSave("bottom", 50000, false),
        ...switchLanguage(secondLanguage),
        {
            content: "Ensure English page is NOT updated",
            trigger: ":iframe h1:not(:contains(Yet another))",
        },
        ...openTranslate(),
        {
            content: "Ensure English page is updated",
            trigger: ":iframe h1:contains(Yet another)",
        },
        {
            content: "Translate again",
            trigger: ":iframe h1 [data-oe-translation-state=to_translate]",
            run: "editor Yet another translated text",
        },
        ...saveTranslation(),
        {
            content: "Check translation is displayed",
            trigger: ":iframe h1:contains(Yet another translated text)",
        },
        // xml record
        {
            content: "Go to test_view page",
            trigger: ":iframe main section.s_banner a",
            run: "click",
        },
        {
            content: "Wait until page is reached",
            trigger: ":iframe body:contains(Test View)",
        },
        ...switchLanguage(mainLanguage),
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Edit template text",
            trigger: ":iframe main p.o_editable[contenteditable='true']",
            run: "editor Modified View",
        },
        ...clickOnSave("bottom", 50000, false),
        ...switchLanguage(secondLanguage),
        ...openTranslate(),
        {
            content: "Translate test view",
            trigger: ":iframe main > p > span[data-oe-translation-state=to_translate]",
            run: "editor Some translated view",
        },
        ...saveTranslation(),
        {
            content: "Check translation is displayed",
            trigger: ":iframe p:contains(Some translated view)",
        },
        ...switchLanguage(mainLanguage),
        ...openHtmlEditor(),
        {
            content: "Change text",
            trigger: 'div.ace_line .ace_xml:contains("test_website.test_view")',
            run() {
                window.ace.edit(document.querySelector("#resource-editor div"))
                   .getSession()
                   .insert({row: 2, column: 36}, 'Further ');
            },
        },
        ...saveHtmlEditor(),
        {
            content: "Ensure view is updated",
            trigger: ":iframe body:contains(Further Modified View)",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Edit template text",
            trigger: ":iframe main p.o_editable[data-oe-field='arch'][contenteditable='true']",
            run: "editor Even more modified Text",
        },
        ...clickOnSave("bottom", 50000, false),
        ...switchLanguage(secondLanguage),
        {
            content: "Check old translation is displayed",
            trigger: ":iframe p:contains(Some translated view)",
        },
        ...openTranslate(),
        {
            content: "Check new original is displayed",
            trigger: ":iframe p:contains(Even more modified text)",
        },
        {
            content: "Translate test view",
            trigger: ":iframe main > p > span[data-oe-translation-state=to_translate]",
            run: "editor Even more translated text",
        },
        ...saveTranslation(),
        {
            content: "Check new translation is displayed",
            trigger: ":iframe p:contains(Even more translated text)",
        },
    ];
}

registerWebsitePreviewTour(
    "translation_multi_language_fr_user_fr_en_site",
    {
        url: "/fr",
    },
    () => [
        ensureFrUser,
        ensureFrSite,
        ...multiLanguage("fr", "en"),
    ]
);

registerWebsitePreviewTour(
    "translation_multi_language_fr_user_en_fr_site",
    {
        url: "/en",
    },
    () => [
        ensureFrUser,
        ensureEnSite,
        ...multiLanguage("en", "fr"),
    ]
);

registerWebsitePreviewTour(
    "translation_multi_language_en_user_fr_en_site",
    {
        url: "/fr",
    },
    () => [
        ensureEnUser,
        ensureFrSite,
        ...multiLanguage("fr", "en"),
    ]
);

registerWebsitePreviewTour(
    "translation_multi_language_en_user_en_fr_site",
    {
        url: "/en",
    },
    () => [
        ensureEnUser,
        ensureEnSite,
        ...multiLanguage("en", "fr"),
    ]
);
