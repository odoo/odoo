/** @odoo-module */

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('edit_menus', {
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
    {
        content: "Confirm the mega menu label",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Save the new menu",
        trigger: '.modal-footer .btn-primary',
        extra_trigger: '.oe_menu_editor [data-is-mega-menu="true"] .js_menu_label:contains("Megaaaaa!")',
    },
    wTourUtils.clickOnExtraMenuItem({extra_trigger: 'body:not(:has(.oe_menu_editor))'}, true),
    {
        content: "There should be a new megamenu item.",
        trigger: 'iframe #top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa!")',
        run: () => {}, // It's a check.
    },
    // Add a menu item in edit mode.
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Click on a menu item",
        trigger: 'iframe #top_menu .nav-item a',
    },
    {
        content: "Click on Edit Menu",
        trigger: 'iframe .o_edit_menu_popover a.js_edit_menu',
    },
    {
        content: "Trigger the link dialog (click 'Add Menu Item')",
        extra_trigger: '.o_website_dialog:visible',
        trigger: '.modal-body a:eq(0)',
    },
    {
        content: "Confirm the new menu entry without a label",
        extra_trigger: '.modal-dialog .o_website_dialog input:eq(0)',
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "It didn't save without a label. Fill label input.",
        extra_trigger: '.o_website_dialog:eq(1):visible',
        trigger: '.modal-dialog .o_website_dialog input:eq(0)',
        run: 'text Random!',
    },
    {
        content: "Confirm the new menu entry without a url",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "It didn't save without a url. Fill url input.",
        trigger: '.modal-dialog .o_website_dialog input:eq(1)',
        extra_trigger: '.modal-dialog .o_website_dialog input.is-invalid',
        run: 'text #',
    },
    {
        content: "Confirm the new menu entry",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Save the website menu with the new entry",
        trigger: '.modal-footer .btn-primary',
        extra_trigger: '.oe_menu_editor .js_menu_label:contains("Random!")',
    },
    // Edit the new menu item from the "edit link" popover button
    wTourUtils.clickOnExtraMenuItem({extra_trigger: '#oe_snippets.o_loaded'}, true),
    {
        content: "Menu should have a new link item",
        trigger: 'iframe #top_menu .nav-item a:contains("Random!")',
    },
    {
        content: "navbar shouldn't have any zwnbsp and no o_link_in_selection class",
        trigger: 'iframe nav.navbar:not(:has(.o_link_in_selection)):not(:contains("\ufeff"))',
        run: () => {}, // It's a check.
    },
    {
        content: "Click on Edit Link",
        trigger: 'iframe .o_edit_menu_popover a.o_we_edit_link',
    },
    {
        content: "Change the label",
        trigger: '.modal-dialog .o_website_dialog input:eq(0)',
        run: 'text Modnar',
    },
    {
        content: "Confirm the new label",
        trigger: '.modal-footer .btn-primary',
    },
    ...wTourUtils.clickOnSave(),
    wTourUtils.clickOnExtraMenuItem({extra_trigger: 'iframe body:not(.editor_enable)'}, true),
    {
        content: "Label should have changed",
        extra_trigger: "iframe body:not(.editor_enable)",
        trigger: 'iframe #top_menu .nav-item a:contains("Modnar")',
        run: () => {}, // it's a check
    },
    // Edit the menu item from the "edit menu" popover button
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.clickOnExtraMenuItem({}, true),
    {
        content: "Click on the 'Modnar' link",
        trigger: 'iframe #top_menu .nav-item a:contains("Modnar")',
    },
    {
        content: "Click on the popover Edit Menu button",
        trigger: 'iframe .o_edit_menu_popover a.js_edit_menu',
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
    {
        content: "Confirm the new menu label",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Save the website menu with the new menu label",
        trigger: '.modal-footer .btn-primary',
        extra_trigger: '.oe_menu_editor .js_menu_label:contains("Modnar !!")',
    },
    // Drag a block to be able to scroll later.
    wTourUtils.dragNDrop({id: 's_media_list', name: 'Media List'}),
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
    // Drag the Mega menu to the first position.
    {
        content: "Drag Mega at the top",
        trigger: '.oe_menu_editor li:contains("Megaaaaa!") > .ui-sortable-handle',
        run: "drag_move_and_drop [0,0]@.oe_menu_editor li:contains('Home') > .ui-sortable-handle => .oe_menu_editor li",
    },
    {
        content: "Wait for drop",
        trigger: '.oe_menu_editor:first-child:contains("Megaaaaa!")',
        run: () => {}, // It's a check.
    },
    {
        content: "Save the website menu with new nested menus",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Menu item should have a child",
        trigger: 'iframe #top_menu .nav-item a.dropdown-toggle:contains("Home")',
    },
    // Check that with the auto close of dropdown menus, the dropdowns remain
    // openable.
    {
        content: "When menu item is opened, child item must appear in the shown menu",
        trigger: 'iframe #top_menu .nav-item:contains("Home") ul.show li a.dropdown-item:contains("Contact us")[href="/contactus"]',
        run: function () {
            // Scroll down.
            this.$anchor[0].closest('body').querySelector('.o_footer_copyright_name')
                .scrollIntoView(true);
        },
    },
    {
        content: "The Home menu should be closed",
        trigger: 'iframe #top_menu .nav-item:contains("Home"):has(ul:not(.show))',
        run: () => {}, // It's a check.
    },
    {
        content: "Open the Home menu after scroll",
        trigger: 'iframe #top_menu .nav-item a.dropdown-toggle:contains("Home")',
    },
    {
        content: "Check that the Home menu is opened",
        trigger: 'iframe #top_menu .nav-item:contains("Home") ul.show li' +
            ' a.dropdown-item:contains("Contact us")[href="/contactus"]',
        run: () => {}, // It's a check.
    },
    {
        content: "Close the Home menu",
        trigger: 'iframe #top_menu .nav-item:has(a.dropdown-toggle:contains("Home"))',
    },
    {
        content: "Check that the Home menu is closed",
        trigger: 'iframe #top_menu .nav-item:contains("Home"):has(ul:not(.show))',
        run: () => {}, // It's a check.
    },
    {
        content: "Open the mega menu",
        trigger: 'iframe #top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa!")',
    },
    {
        content: "When the mega menu is opened, scroll up",
        trigger: 'iframe #top_menu .o_mega_menu_toggle.show',
        run: function () {
            const marginTopOfMegaMenu = getComputedStyle(
                this.$anchor[0].closest('.dropdown').querySelector('.o_mega_menu'))['margin-top'];
            if (marginTopOfMegaMenu !== '0px') {
                console.error('The margin-top of the mega menu should be 0px');
            }
            // Scroll up.
            this.$anchor[0].closest('body').querySelector('.s_media_list_item:nth-child(2)')
                .scrollIntoView(true);
        }
    },
    {
        content: "Check that the mega menu is closed",
        trigger: 'iframe #top_menu .nav-item:contains("Megaaaaa!"):has(div[data-name="Mega Menu"]:not(.show))',
        run:() => {}, // It's a check.
    },
    {
        content: "Open the mega menu after scroll",
        trigger: 'iframe #top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa!")',
    },
    {
        content: "Check that the mega menu is opened",
        trigger: 'iframe #top_menu .nav-item:has(a.o_mega_menu_toggle:contains("Megaaaaa!")) ' +
                 '.s_mega_menu_odoo_menu',
        run: () => {}, // It's a check.
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Open nested menu item",
        trigger: 'iframe #top_menu .nav-item:contains("Home"):nth(1) .dropdown-toggle',
    },
    {
        // If this step fails, it means that a patch inside bootstrap was lost.
        content: "Press the 'down arrow' key.",
        trigger: 'iframe #top_menu .nav-item:contains("Home") li:contains("Contact us")',
        run: function (actions) {
            this.$anchor[0].dispatchEvent(new window.KeyboardEvent("keydown", { key: "ArrowDown" }));
        },
    },
]);
