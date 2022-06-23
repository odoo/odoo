/** @odoo-module */

import wTourUtils from 'website.tour_utils';

const clickOnSave = {
   content: "Clicks on the menu edition dialog save button",
   trigger: '.modal-dialog .btn-primary:contains("Ok"), .modal-dialog .btn-primary:contains("Save")',
};

wTourUtils.registerEditionTour('edit_menus', {
    test: true,
    url: '/',
}, [
    // Add a megamenu item from the menu.
    {
        content: "open site menu",
        extra_trigger: "iframe #wrapwrap",
        trigger: 'button[data-menu-xmlid="website.menu_site"]',
    },
    {
        content: "Click on Edit Menu",
        trigger: 'a[data-menu-xmlid="website.menu_edit_menu"]',
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
    clickOnSave,
    Object.assign({}, clickOnSave, {extra_trigger: '.o_dialog_container:not(:has(.o_inactive_modal))'}),
    wTourUtils.clickOnExtraMenuItem({extra_trigger: 'body:not(:has(.oe_menu_editor))'}, true),
    {
        content: "There should be a new megamenu item.",
        trigger: 'iframe #top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa!")',
        run: () => {}, // It's a check.
    },
    // Add a menu item in edit mode.
    wTourUtils.clickOnEdit(),
    {
        content: "Click on a menu item",
        trigger: 'iframe #top_menu .nav-item a',
        extra_trigger: '#oe_snippets.o_loaded',
    },
    {
        content: "Click on Edit Menu",
        trigger: '.o_edit_menu_popover a.js_edit_menu',
    },
    {
        content: "Trigger the link dialog (click 'Add Menu Item')",
        extra_trigger: '.o_website_dialog:visible',
        trigger: '.modal-body a:eq(0)',
    },
    clickOnSave,
    {
        content: "It didn't save without a label. Fill label input.",
        extra_trigger: '.o_website_dialog:eq(1):visible',
        trigger: '.modal-dialog .o_website_dialog input:eq(0)',
        run: 'text Random!',
    },
    clickOnSave,
    {
        content: "It didn't save without a url. Fill url input.",
        trigger: '.modal-dialog .o_website_dialog input:eq(1)',
        run: 'text #',
    },
    clickOnSave,
    Object.assign({}, clickOnSave, {extra_trigger: '.o_dialog_container:not(:has(.o_inactive_modal))'}),
    // Edit the new menu item from the "edit link" popover button
    wTourUtils.clickOnExtraMenuItem({extra_trigger: '#oe_snippets.o_loaded'}, true),
    {
        content: "Menu should have a new link item",
        trigger: 'iframe #top_menu .nav-item a:contains("Random!")',
    },
    {
        content: "Click on Edit Link",
        trigger: '.o_edit_menu_popover a.o_we_edit_link',
    },
    {
        content: "Change the label",
        trigger: '.modal-dialog .o_website_dialog input:eq(0)',
        run: 'text Modnar',
    },
    clickOnSave,
    ...wTourUtils.clickOnSave(),
    wTourUtils.clickOnExtraMenuItem({extra_trigger: 'iframe body:not(.editor_enable)'}, true),
    {
        content: "Label should have changed",
        extra_trigger: "iframe body:not(.editor_enable)",
        trigger: 'iframe #top_menu .nav-item a:contains("Modnar")',
        run: () => {}, // it's a check
    },
    // Edit the menu item from the "edit menu" popover button
    wTourUtils.clickOnEdit(),
    {
        content: "Click on the 'Modnar' link",
        extra_trigger: "#oe_snippets.o_loaded",
        trigger: 'iframe #top_menu .nav-item a:contains("Modnar")',
    },
    {
        content: "Click on the popover Edit Menu button",
        trigger: '.o_edit_menu_popover a.js_edit_menu',
    },
    {
        content: "Click on the dialog Edit Menu button",
        trigger: '.oe_menu_editor .js_menu_label:contains("Modnar")',
        run: function () {
            const liEl = this.$anchor[0].closest('[data-menu-id]');
            liEl.querySelector('button.js_edit_menu').click();
        },
    },
    {
        content: "Change the label",
        trigger: '.modal-dialog .o_website_dialog input:eq(0)',
        run: 'text Modnar !!',
    },
    clickOnSave,
    Object.assign({}, clickOnSave, {extra_trigger: '.o_dialog_container:not(:has(.o_inactive_modal))'}),
    ...wTourUtils.clickOnSave(),
    wTourUtils.clickOnExtraMenuItem({extra_trigger: 'iframe body:not(.editor_enable)'}, true),
    {
        content: "Label should have changed",
        trigger: 'iframe #top_menu .nav-item a:contains("Modnar !!")',
        run: () => {}, // It's a check.
    },
    // Nest menu item from the menu.
    {
        content: "open site menu",
        trigger: 'button[data-menu-xmlid="website.menu_site"]',
    },
    {
        content: "Click on Edit Menu",
        trigger: 'a[data-menu-xmlid="website.menu_edit_menu"]',
    },
    {
        content: "Drag item into parent",
        trigger: '.oe_menu_editor li:contains("Contact us") > .ui-sortable-handle',
        // Menu rows are 38px tall.
        run: "drag_move_and_drop [50,38]@.oe_menu_editor li:contains('Home') > .ui-sortable-handle => .oe_menu_editor li:contains('Home') .ui-sortable-placeholder",
    },
    {
        content: "Wait for drop",
        trigger: '.oe_menu_editor li:contains("Home") ul li:contains("Contact us")',
        run: () => {}, // It's a check.
    },
    clickOnSave,
    {
        content: "Menu item should have a child",
        trigger: 'iframe #top_menu .nav-item a.dropdown-toggle:contains("Home")',
    },
    {
        content: "When menu item is opened, child item must appear in the shown menu",
        trigger: 'iframe #top_menu .nav-item:contains("Home") ul.show li a.dropdown-item:contains("Contact us")[href="/contactus"]',
        run: () => {}, // It's a check.
    },
]);
