odoo.define("website.tour.edit_megamenu", function (require) {
"use strict";

const tour = require('web_tour.tour');

tour.register('edit_megamenu', {
    test: true,
    url: '/?enable_editor=1',
}, [
    // Add a megamenu item to the top menu.
    {
        content: "Click on a menu item",
        trigger: '#top_menu .nav-item a',
    },
    {
        content: "Click on 'Link' to open Link Dialog",
        trigger: '.o_edit_menu_popover a.js_edit_menu',
    },
    {
        content: "Trigger the link dialog (click 'Add Mega Menu Item')",
        extra_trigger: '.o_web_editor_dialog:visible',
        trigger: '.modal-body a.js_add_menu[data-type="mega"]',
    },
    {
        content: "Write a label for the new menu item",
        extra_trigger: '.o_link_dialog',
        trigger: '.o_link_dialog #o_link_dialog_label_input',
        run: 'text Megaaaaa!'
    },
    {
        content: "Save the new menu item",
        trigger: '.modal-dialog .btn-primary span:contains("Save")',
        run: 'click',
    },
    {
        content: "Save the changes to the menu",
        trigger: '.modal-dialog .btn-primary span:contains("Save")',
        run: 'click',
    },
    {
        content: "Menu should have a new megamenu item",
        trigger: '#top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa!")',
        run: function () {}, // it's a check
    },
]);
});
