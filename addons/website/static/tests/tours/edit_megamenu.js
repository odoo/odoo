/** @odoo-module **/

import {
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
        content: "Edit link",
        trigger: "#create-link",
        run: "click",
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
