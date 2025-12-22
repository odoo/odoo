/** @odoo-module **/

import {
    selectHeader,
    clickOnEditAndWaitEditMode,
    changeOption,
    clickOnExtraMenuItem,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

const toggleMegaMenu = (stepOptions) => Object.assign({}, {
    content: "Toggles the mega menu.",
    trigger: ":iframe .top_menu .nav-item a.o_mega_menu_toggle",
    run(helpers) {
        // If the mega menu is displayed inside the extra menu items, it should
        // already be displayed.
        if (!this.anchor.closest(".o_extra_menu_items")) {
            helpers.click();
        }
    },
}, stepOptions);

registerWebsitePreviewTour('edit_megamenu', {
    url: '/',
    edition: true,
}, () => [
    // Add a megamenu item to the top menu.
    {
        content: "Click on a menu item",
        trigger: ":iframe .top_menu .nav-item a",
        run: "click",
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        trigger: ':iframe .o_edit_menu_popover a.js_edit_menu',
        run: "click",
    },
    {
        trigger: ".o_website_dialog:visible",
    },
    {
        content: "Trigger the link dialog (click 'Add Mega Menu Item')",
        trigger: '.modal-body a:eq(1)',
        run: "click",
    },
    {
        content: "Write a label for the new menu item",
        trigger: '.modal-dialog .o_website_dialog input',
        run: "edit Megaaaaa!",
    },
    {
        content: "Confirm the mega menu label",
        trigger: ".modal .modal-footer button:contains(ok)",
        run: "click",
    },
    {
        trigger: '.oe_menu_editor [data-is-mega-menu="true"] .js_menu_label:contains("Megaaaaa!")',
    },
    {
        content: "Save the website menu with a new mega menu",
        trigger: ".modal .modal-footer button:contains(save)",
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    {
        trigger: '#oe_snippets.o_loaded',
    },
    {
        trigger: ".o_website_preview.editor_enable.editor_has_snippets:not(.o_is_blocked)"
    },
    // Edit a menu item
    clickOnExtraMenuItem({}, true),
    toggleMegaMenu({}),
    {
        content: "Select the last menu link of the first column",
        trigger: ':iframe .s_mega_menu_odoo_menu .row > div:first-child .nav > :nth-child(6)', // 6th is the last one
        run: "click",
    },
    {
        content: "Hit the delete button to remove the menu link",
        trigger: ':iframe .oe_overlay .oe_snippet_remove',
        run: "click",
    },
    {
        content: "Check that the last menu link was deleted",
        trigger: ':iframe .s_mega_menu_odoo_menu .row > div:first-child .nav:not(:has(:nth-child(6)))',
    },
    {
        content: "Click on the first title item.",
        trigger: ':iframe .o_mega_menu h4',
        run: "click",
    },
    {
        content: "Press enter.",
        trigger: ':iframe .o_mega_menu h4',
        run() {
            this.anchor.dispatchEvent(
                new window.InputEvent("input", {bubbles: true, inputType: "insertParagraph"})
            );
        },
    },
    {
        content: "The menu should still be visible. Edit a menu item.",
        trigger: ':iframe .o_mega_menu h4',
        // The content is removed in the previous step so it's now invisible.
        run: "editor New Menu Item",
    },
    {
        // If this step fails, it means that a patch inside bootstrap was lost.
        content: "Press the 'down arrow' key.",
        trigger: ':iframe .o_mega_menu h4',
        run: "press ArrowDown",
    },
    ...clickOnSave(),
    clickOnExtraMenuItem({}, true),
    toggleMegaMenu(),
    {
        content: "The menu item should have been renamed.",
        trigger: ':iframe .o_mega_menu h4:contains("New Menu Item")',
    },
]);
registerWebsitePreviewTour("megamenu_active_nav_link", {
    url: "/",
    edition: true,
}, () => [
       // Add a megamenu item to the top menu.
    {
        content: "Click on a menu item",
        trigger: ":iframe .top_menu .nav-item a",
        run: "click",
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        trigger: ":iframe .o_edit_menu_popover a.js_edit_menu",
        run: "click",
    },
    {
        trigger: ".o_website_dialog",
    },
    {
        content: "Trigger the link dialog (click 'Add Mega Menu Item')",
        trigger: ".modal-body a:eq(1)",
        run: "click",
    },
    {
        content: "Write a label for the new menu item",
        trigger: ".modal-dialog .o_website_dialog input",
        run: "edit MegaTron",
    },
    {
        content: "Confirm the mega menu label",
        trigger: ".modal .modal-footer .btn-primary:contains(ok)",
        run: "click",
    },
    {
        trigger: `.oe_menu_editor [data-is-mega-menu="true"] .js_menu_label:contains("MegaTron")`,
    },
    {
        content: "Save the website menu with a new mega menu",
        trigger: ".modal-footer .btn-primary",
        run: "click",
    },
    {
        trigger: "#oe_snippets.o_loaded",
    },
    {
        content: "Check for the new mega menu",
        trigger: `:iframe .top_menu:has(.nav-item a.o_mega_menu_toggle:contains("Megatron"))`,
    },
    {
        trigger: ".o_website_preview.editor_enable.editor_has_snippets:not(.o_is_blocked)"
    },
    clickOnExtraMenuItem({}, true),
    toggleMegaMenu({}),
    {
        content: "Select the last menu link of the first column",
        trigger: ":iframe .s_mega_menu_odoo_menu .row > div:first-child .nav > :nth-child(6)",
        run: "click",
    },
    {
        content: "Click 'edit link' button if URL input is now shown",
        trigger: "#create-link",
        async run(actions) {
            // Note: the 'create-link' button is always here, however the input 
            // for the URL might not be.
            // We have to consider both cases:
            // 1. Single-app website build: a few menu, so no extra menu added 
            //    and the URL input is shown
            // 2. Multi-app website build:  many menu, so extra menu added 
            //    and the URL input is not shown
            if (!document.querySelector("#o_link_dialog_url_input")) {
                await actions.click();
            }
        },
    },
    {
        content: "Change the link",
        trigger: "#o_link_dialog_url_input",
        run: "edit /new_page"
    },
    ...clickOnSave(),
    clickOnExtraMenuItem({}, true),
    toggleMegaMenu(),
    {
        content: "Click on the last menu link of the first column",
        trigger: ":iframe .s_mega_menu_odoo_menu .row > div:first-child .nav > :nth-child(6)",
        run: "click",
    },
    {
        content: "Check if the new mega menu is active",
        trigger: `:iframe .top_menu:has(.nav-item a.o_mega_menu_toggle.active:contains("MegaTron"))`,
    },
])
registerWebsitePreviewTour('edit_megamenu_big_icons_subtitles', {
    url: '/',
    edition: true,
}, () => [
    // Add a megamenu item to the top menu.
    {
        content: "Click on a menu item",
        trigger: ':iframe .top_menu .nav-item a',
        run: "click",
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        trigger: ':iframe .o_edit_menu_popover a.js_edit_menu',
        run: "click",
    },
    {
        trigger: ".o_website_dialog",
    },
    {
        content: "Trigger the link dialog (click 'Add Mega Menu Item')",
        trigger: '.modal-body a:eq(1)',
        run: "click",
    },
    {
        content: "Write a label for the new menu item",
        trigger: '.modal-dialog .o_website_dialog input',
        run: "edit Megaaaaa2!",
    },
    {
        content: "Confirm the mega menu label",
        trigger: ".modal .modal-footer .btn-primary:contains(ok)",
        run: "click",
    },
    {
        trigger: '.oe_menu_editor [data-is-mega-menu="true"] .js_menu_label:contains("Megaaaaa2!")',
    },
    {
        content: "Save the website menu with a new mega menu",
        trigger: '.modal-footer .btn-primary',
        run: "click",
    },
    {
        trigger: '#oe_snippets.o_loaded',
    },
    {
        content: "Check for the new mega menu",
        trigger: ':iframe .top_menu:has(.nav-item a.o_mega_menu_toggle:contains("Megaaaaa2!"))',
    },
    {
        trigger: ".o_website_preview.editor_enable.editor_has_snippets:not(.o_is_blocked)"
    },
    // Edit a menu item
    clickOnExtraMenuItem({}, true),
    toggleMegaMenu({}),
    {
        content: "Select the first menu link of the first column",
        trigger: ':iframe .s_mega_menu_odoo_menu .row > div:first-child .nav > :first-child',
        run: "click",
    },
    changeOption("MegaMenuLayout", "we-toggler"),
    {
        content: "Select Big Icons Subtitles mega menu",
        trigger: '[data-select-label="Big Icons Subtitles"]',
        run: "click",
    },
    {
        content: "Select the h4 of first menu link of the first column",
        trigger: ':iframe .s_mega_menu_big_icons_subtitles .row > div:first-child .nav > :first-child h4',
        async run(actions) {
            // Clicking on the h4 element first time leads to the selection of
            // the entire a.nav-link, due to presence of `o_default_snippet_text` class
            // hence, specify the selection on the h4 element
            await actions.click();
            const iframeDocument = document.querySelector('.o_iframe').contentDocument;
            const range = iframeDocument.createRange();
            range.selectNodeContents(this.anchor);
            const sel = iframeDocument.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        },
    },
    {
        content: "Convert it to Bold",
        trigger: '#oe_snippets #toolbar #bold',
        run: "click",
    },
    ...clickOnSave(),
    clickOnExtraMenuItem({}, true),
    toggleMegaMenu(),
    {
        content: "The menu item should only convert selected text to Bold.",
        trigger: ':iframe .s_mega_menu_big_icons_subtitles .row > div:first-child .nav > :first-child span:not(:has(strong))',
    },
]);

const createMegaMenu = function (name) {
    return [
        {
            content: "Create a new mega menu item",
            trigger: ".modal-body a:eq(1)",
            run: "click",
        },
        {
            content: "Set the mega menu item name to " + name,
            trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_website_dialog input:eq(0)",
            run: "edit " + name,
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(ok)",
            run: "click",
        },
    ];
};

const createDropdown = function (name) {
    return [
        {
            content: "Create a new menu item for the dropdown",
            trigger: ".modal-body a:eq(0)",
            run: "click",
        },
        {
            content: "Set the dropdown name to " + name,
            trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_website_dialog input:eq(0)",
            run: "edit " + name,
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_website_dialog input:eq(1)",
            run: "edit /",
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(ok)",
            run: "click",
        },
        {
            content: "Create a new menu item for the dropdown item",
            trigger: ".modal-body a:eq(0)",
            run: "click",
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_website_dialog input:eq(0)",
            run: "edit " + name + " item",
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_website_dialog input:eq(1)",
            run: "edit /",
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(ok)",
            run: "click",
        },
        {
            content: "Move the dropdown item into the dropdown",
            trigger: '.oe_menu_editor li:contains("' + name + " item" + '") .fa-bars',
            run(helpers) {
                return helpers.drag_and_drop('.oe_menu_editor li:contains("' + name + '")', {
                    position: {
                        left: 50,
                    },
                    relative: true,
                });
            },
        },
    ];
};

const testHeaderNavVisibility = function (elementsVisibility) {
    const test = [];
    for (const [menu, visibility] of Object.entries(elementsVisibility)) {
        test.push({
            trigger: `:iframe .top_menu li:contains('${menu}')${
                visibility ? ":visible" : ":not(:visible)"
            }`,
        });
    }
    return test;
};

const openMenu = () => ({
    content: "Open Menu",
    trigger: ":iframe span.navbar-toggler-icon",
    run: "click",
});

registerWebsitePreviewTour(
    "edit_megamenu_visibility",
    {
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Click on a menu item",
            trigger: ":iframe .top_menu .nav-item a",
            run: "click",
        },
        {
            content: "Click on Edit Menu",
            trigger: ":iframe .o_edit_menu_popover a.js_edit_menu",
            run: "click",
        },
        {
            trigger: ".o_website_dialog:visible",
        },
        ...createMegaMenu("MM des"),
        ...createDropdown("Drop 1"),
        ...createMegaMenu("MM mob"),
        ...createDropdown("Drop 2"),
        ...createMegaMenu("MM cond"),
        {
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(save)",
            run: "click",
        },
        selectHeader(),
        changeOption("WebsiteLevelColor", 'we-select[data-variable="header-template"] we-toggler'),
        changeOption("WebsiteLevelColor", 'we-button[data-name="header_hamburger_opt"]'),
        openMenu(),
        // Mega Menu 1: Desktop Only
        {
            content: "Open the first mega menu",
            trigger: ":iframe header#top span:contains('MM des')",
            run: "click",
        },
        {
            content: "Click on the first mega menu content",
            trigger: ":iframe header#top div.o_mega_menu.show section",
            run: "click",
        },
        changeOption(
            "ConditionalVisibility",
            'we-button[data-toggle-device-visibility="no_mobile"]'
        ),
        // Mega Menu 2: Mobile Only
        {
            content: "Open the second mega menu",
            trigger: ":iframe header#top span:contains('MM mob')",
            run: "click",
        },
        {
            content: "Click on the second mega menu content",
            trigger: ":iframe header#top div.o_mega_menu.show section",
            run: "click",
        },
        changeOption(
            "ConditionalVisibility",
            'we-button[data-toggle-device-visibility="no_desktop"]'
        ),
        // Mega Menu 3: Logged Out Only
        {
            content: "Open the third mega menu",
            trigger: ":iframe header#top span:contains('MM cond')",
            run: "click",
        },
        {
            content: "Click on the third mega menu content",
            trigger: ":iframe header#top div.o_mega_menu.show section",
            run: "click",
        },
        changeOption("ConditionalVisibility", 'we-toggler:contains("No Condition")'),
        changeOption("ConditionalVisibility", 'we-button:contains("Conditionally")'),
        changeOption("ConditionalVisibility", 'we-toggler:contains("Visible for Everyone")'),
        changeOption("ConditionalVisibility", 'we-button:contains("Visible for Logged Out")'),
        ...clickOnSave(),
        // Check desktop visibility while NOT editing
        openMenu(),
        ...testHeaderNavVisibility({
            "MM des": true,
            "Drop 1": true,
            "MM mob": false,
            "Drop 2": true,
            "MM cond": false,
        }),
        {
            content: "Switch to mobile view",
            trigger: ".o_mobile_preview > a",
            run: "click",
        },
        openMenu(),
        // Check mobile visibility while NOT editing
        ...testHeaderNavVisibility({
            "MM des": false,
            "Drop 1": true,
            "MM mob": true,
            "Drop 2": true,
            "MM cond": false,
        }),
        ...clickOnEditAndWaitEditMode(),
        // Check mobile visibility while editing
        ...testHeaderNavVisibility({
            "MM des": true,
            "Drop 1": true,
            "MM mob": true,
            "Drop 2": true,
            "MM cond": true,
        }),
        {
            content: "Switch to desktop view",
            trigger: "button:has(> span.fa-mobile)",
            run: "click",
        },
        // Check desktop visibility while editing
        openMenu(),
        ...testHeaderNavVisibility({
            "MM des": true,
            "Drop 1": true,
            "MM mob": true,
            "Drop 2": true,
            "MM cond": true,
        }),
    ]
);
