odoo.define("website.tour.edit_megamenu", function (require) {
"use strict";

const wTourUtils = require('website.tour_utils');

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
}, [
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
    // Edit a menu item
    wTourUtils.clickOnExtraMenuItem({extra_trigger: '#oe_snippets.o_loaded'}, true),
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
        run: 'text New Menu Item',
    },
    ...wTourUtils.clickOnSave(),
    wTourUtils.clickOnExtraMenuItem({extra_trigger: 'iframe body:not(.editor_enable)'}, true),
    toggleMegaMenu(),
    {
        content: "The menu item should have been renamed.",
        trigger: 'iframe .o_mega_menu h4:contains("New Menu Item")',
        run: function () {}, // it's a check
    },
]);
});
