/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

const toggleMegaMenu = (stepOptions) => Object.assign({}, {
    content: "Toggles the mega menu.",
    trigger: 'iframe #top_menu .nav-item a.o_mega_menu_toggle',
    run: function () {
        // If the mega menu is displayed inside the extra menu items, it should
        // already be displayed.
        if (!this.$anchor[0].closest('.o_extra_menu_items')) {
            this.$anchor[0].dispatchEvent(new Event('click'))
        }
    },
}, stepOptions);

wTourUtils.registerWebsitePreviewTour('edit_megamenu', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    // Add a megamenu item to the top menu.
    {
        content: "Click on a menu item",
        trigger: 'iframe #top_menu .nav-item a',
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        trigger: 'iframe .o_edit_menu_popover a.js_edit_menu',
    },
    {
        content: "Trigger the link dialog (click 'Add Mega Menu Item')",
        extra_trigger: '.o_website_dialog:visible',
        trigger: '.modal-body a:eq(1)',
    },
    {
        content: "Write a label for the new menu item",
        trigger: '.modal-dialog .o_website_dialog input',
        run: 'text Megaaaaa!'
    },
    {
        content: "Confirm the mega menu label",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Save the website menu with a new mega menu",
        trigger: '.modal-footer .btn-primary',
        extra_trigger: '.oe_menu_editor [data-is-mega-menu="true"] .js_menu_label:contains("Megaaaaa!")',
    },
    {
        trigger: '#oe_snippets.o_loaded',
        run() {},
    },
    // Edit a menu item
    wTourUtils.clickOnExtraMenuItem({extra_trigger: ".o_website_preview.editor_enable.editor_has_snippets:not(.o_is_blocked)"}, true),
    toggleMegaMenu({extra_trigger: 'iframe #top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa!")'}),
    {
        content: "Select the last menu link of the first column",
        trigger: 'iframe .s_mega_menu_odoo_menu .row > div:first-child .nav > :nth-child(6)', // 6th is the last one
    },
    {
        content: "Hit the delete button to remove the menu link",
        trigger: 'iframe .oe_overlay .oe_snippet_remove',
    },
    {
        content: "Check that the last menu link was deleted",
        trigger: 'iframe .s_mega_menu_odoo_menu .row > div:first-child .nav:not(:has(> :nth-child(6)))',
        run: () => null,
    },
    {
        content: "Clicks on the first title item.",
        trigger: 'iframe .o_mega_menu h4',
    },
    {
        content: "Press enter.",
        trigger: 'iframe .o_mega_menu h4',
        run: function (actions) {
            this.$anchor[0].dispatchEvent(new window.InputEvent('input', {bubbles: true, inputType: 'insertParagraph'}));
        },
    },
    {
        content: "The menu should still be visible. Edit a menu item.",
        trigger: 'iframe .o_mega_menu h4',
        // The content is removed in the previous step so it's now invisible.
        allowInvisible: true,
        run: 'text New Menu Item',
    },
    ...wTourUtils.clickOnSave(),
    wTourUtils.clickOnExtraMenuItem({}, true),
    toggleMegaMenu(),
    {
        content: "The menu item should have been renamed.",
        trigger: 'iframe .o_mega_menu h4:contains("New Menu Item")',
        run: function () {}, // it's a check
    },
]);
wTourUtils.registerWebsitePreviewTour('edit_megamenu_big_icons_subtitles', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    // Add a megamenu item to the top menu.
    {
        content: "Click on a menu item",
        trigger: 'iframe #top_menu .nav-item a',
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        trigger: 'iframe .o_edit_menu_popover a.js_edit_menu',
    },
    {
        content: "Trigger the link dialog (click 'Add Mega Menu Item')",
        extra_trigger: ".o_website_dialog",
        trigger: '.modal-body a:eq(1)',
    },
    {
        content: "Write a label for the new menu item",
        trigger: '.modal-dialog .o_website_dialog input',
        run: 'text Megaaaaa2!',
    },
    {
        content: "Confirm the mega menu label",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Save the website menu with a new mega menu",
        trigger: '.modal-footer .btn-primary',
        extra_trigger: '.oe_menu_editor [data-is-mega-menu="true"] .js_menu_label:contains("Megaaaaa2!")',
    },
    {
        trigger: '#oe_snippets.o_loaded',
        run() {},
    },
    {
        content: "Check for the new mega menu",
        trigger: 'iframe #top_menu:has(.nav-item a.o_mega_menu_toggle:contains("Megaaaaa2!"))',
        run: function () {}, // it's a check
    },
    // Edit a menu item
    wTourUtils.clickOnExtraMenuItem({extra_trigger: ".o_website_preview.editor_enable.editor_has_snippets:not(.o_is_blocked)"}, true),
    toggleMegaMenu({extra_trigger: 'iframe #top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa2!")'}),
    {
        content: "Select the first menu link of the first column",
        trigger: 'iframe .s_mega_menu_odoo_menu .row > div:first-child .nav > :first-child',
    },
    wTourUtils.changeOption("MegaMenuLayout", "we-toggler"),
    {
        content: "Select Big Icons Subtitles mega menu",
        trigger: '[data-select-label="Big Icons Subtitles"]',
    },
    {
        content: "Select the h4 of first menu link of the first column",
        trigger: 'iframe .s_mega_menu_big_icons_subtitles .row > div:first-child .nav > :first-child h4',
        run: function (actions) {
            // Clicking on the h4 element first time leads to the selection of
            // the entire a.nav-link, due to presence of `o_default_snippet_text` class
            // hence, specify the selection on the h4 element
            actions.click();
            const iframeDocument = document.querySelector('.o_iframe').contentDocument;
            const range = iframeDocument.createRange();
            range.selectNodeContents(this.$anchor[0]);
            const sel = iframeDocument.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        },
    },
    {
        content: "Convert it to Bold",
        trigger: '#oe_snippets #toolbar #bold',
    },
    ...wTourUtils.clickOnSave(),
    wTourUtils.clickOnExtraMenuItem({}, true),
    toggleMegaMenu(),
    {
        content: "The menu item should only convert selected text to Bold.",
        trigger: 'iframe .s_mega_menu_big_icons_subtitles .row > div:first-child .nav > :first-child span:not(:has(strong))',
        run: function () {}, // it's a check
    },
]);
