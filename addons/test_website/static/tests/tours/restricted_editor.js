import {
    clickOnSave,
    clickOnEditAndWaitEditMode,
    clickOnExtraMenuItem,
    insertSnippet,
    switchToLang,
} from "@website/js/tours/tour_utils";
import { registry } from "@web/core/registry";

const EDIT_BUTTON_SELECTOR =
    "body .o_menu_systray button.o-website-btn-custo-primary:contains(edit)";

const checkNoTranslate = {
    content: "Check there is no translate button",
    trigger: `${EDIT_BUTTON_SELECTOR}:not(.o-dropdown-toggle-custo)`,
};
const translate = [
    {
        content: "Open Edit menu",
        trigger: `${EDIT_BUTTON_SELECTOR}.o-dropdown-toggle-custo`,
        run: "click",
    },
    {
        content: "Click on translate button",
        trigger: ".o_popover .o_translate_website_dropdown_item:contains(translate)",
        run: "click",
    },
];
const closeErrorDialog = [
    {
        content: "Check has error dialog",
        trigger: ".modal:contains(error) .o_error_dialog.modal-content",
    },
    {
        content: "Close error dialog",
        trigger: ".modal .modal-footer button.btn.btn-primary",
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
];
const goToMenuItem = [
    clickOnExtraMenuItem({}, true),
    {
        content: "Navigate to model item page",
        trigger: ":iframe a[href='/test_website/model_item/1']",
        run: "click",
    },
    {
        content: "Wait to land on model item page",
        trigger: ':iframe a[href="/test_website/model_item/1"].nav-link.active:not(:visible)',
    },
];

registry.category("web_tour.tours").add("test_restricted_editor_only", {
    steps: () => [
        // Home
        checkNoTranslate,
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Check icons cannot be dragged",
            trigger: "#snippet_groups .o_snippet[name='Intro'].o_disabled",
            run: function () {
                if (document.querySelector("button.o_snippet_thumbnail_area")) {
                    console.error(
                        "The button to open the add snippet dialog should not be display for restricted editor."
                    );
                }
            },
        },
        ...clickOnSave(),
        ...switchToLang("fr"),
        ...translate,
        ...closeErrorDialog,
        ...switchToLang("en"),
        // Model item
        {
            trigger: ":iframe body:contains(welcome to your)",
        },
        ...goToMenuItem,
        checkNoTranslate,
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Check icons cannot be dragged",
            trigger: "#snippet_groups .o_snippet[name='Intro'].o_disabled",
            run: function () {
                if (document.querySelector("button.o_snippet_thumbnail_area")) {
                    console.error(
                        "The button to open the add snippet dialog should not be display for restricted editor."
                    );
                }
            },
        },
        ...clickOnSave(),
        ...switchToLang("fr"),
        ...translate,
        ...closeErrorDialog,
    ],
});

registry.category("web_tour.tours").add("test_restricted_editor_test_admin", {
    steps: () => [
        // Home
        checkNoTranslate,
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Check icons cannot be dragged",
            trigger: "#snippet_groups .o_snippet[name='Intro'].o_disabled",
        },
        ...clickOnSave(),
        ...switchToLang("fr"),
        ...translate,
        ...closeErrorDialog,
        ...switchToLang("en"),
        // Model item
        ...goToMenuItem,
        checkNoTranslate,
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Check icons can be dragged",
            trigger: "#snippet_groups .o_snippet[name='Intro']:not(.o_disabled)",
        },
        ...insertSnippet({ id: "s_banner", name: "Banner", groupName: "Intro" }),
        {
            content: "Change name",
            trigger: ":iframe [data-oe-expression='record.name']",
            run: "editor New value",
        },
        ...clickOnSave(),
        ...switchToLang("fr"),
        ...translate,
        {
            content: "Close the dialog",
            trigger: ".modal .modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Assure the modal is well closed",
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "Check that html fields are not content editable when translating",
            trigger:
                ":iframe [data-oe-expression='record.website_description']:not([contenteditable='true'])",
        },
        {
            content: "Translate name",
            trigger: ":iframe [data-oe-expression='record.name']",
            run: "editor Nouvelle valeur",
        },
        {
            content: "Translate some banner text",
            trigger: ":iframe [data-oe-expression='record.website_description'] strong",
            run: "editor potentiel.",
        },
        ...clickOnSave(),
    ],
});

registry.category("web_tour.tours").add("test_restricted_editor_tester", {
    steps: () => [
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Footer should not be be editable for restricted user",
            trigger: ":iframe :has(.o_savable) footer:not(.o_savable):not(:has(.o_savable))",
        },
        ...clickOnSave(),
    ],
});
