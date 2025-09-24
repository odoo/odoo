/** @odoo-module */

import { delay } from "@web/core/utils/concurrency";
import { registry } from "@web/core/registry";
import {
    clickOnEditAndWaitEditMode,
    clickOnExtraMenuItem,
    clickOnSave,
    goBackToBlocks,
    insertSnippet,
    openLinkPopup,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registry.category("web_tour.tours").add("parent_child_menu", {
    url: "/odoo/action-website.action_website_menu",
    steps: () => [
        {
            content: "Open Menu Form View",
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            content: "Insert Menu Name",
            trigger: "input[id='name_0']",
            run: "edit Parent",
        },
        {
            content: "Insert Menu URL",
            trigger: "input[id='url_0']",
            run: "edit /parent",
        },
        {
            content: "Click on Save Button",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "Click on Add a line button",
            trigger: "div[name='child_id'] td.o_field_x2many_list_row_add a",
            run: "click",
        },
        {
            content: "Insert Child Menu Name",
            trigger: ".o_dialog input[id='name_0']",
            run: "edit Child",
        },
        {
            content: "Insert Child Menu URL",
            trigger: ".o_dialog input[id='url_0']",
            run: "edit /child",
        },
        {
            content: "Click on Save & Close Button",
            trigger: "button:contains(Save & Close)",
            run: "click",
        },
        {
            content: "Click on Save Button",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "Check the Parent's URL",
            trigger: "div[name='url']:contains('#')",
        },
        {
            content: "Check the Child's URL",
            trigger: "td[name='url']:contains('/child')",
        },
    ],
});

registerWebsitePreviewTour(
    "edit_menus",
    {
        url: "/",
    },
    () => [
        // Add a megamenu item from the menu.
        {
            trigger: ":iframe #wrapwrap",
        },
        {
            content: "open site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "Click on Edit Menu",
            trigger: 'a[data-menu-xmlid="website.menu_edit_menu"]',
            run: "click",
        },
        {
            trigger: ".o_website_dialog:visible",
        },
        {
            content: "Trigger the link dialog (click 'Add Mega Menu Item')",
            trigger: ".modal:not(.o_inactive_modal) .modal-body a:eq(1)",
            run: "click",
        },
        {
            content: "Write a label for the new menu item",
            trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_website_dialog input",
            run: "edit Megaaaaa!",
        },
        {
            content: "Confirm the mega menu label",
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Continue)",
            run: "click",
        },
        {
            trigger:
                '.oe_menu_editor [data-is-mega-menu="true"] .js_menu_label:contains("Megaaaaa!")',
        },
        {
            content: "Save the new menu",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: "body:not(:has(.oe_menu_editor))",
        },
        {
            trigger: ":iframe body:contains(welcome to your)",
        },
        clickOnExtraMenuItem({}, true),
        {
            content: "There should be a new megamenu item.",
            trigger: ':iframe .top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa!")',
        },
        // Add a menu item in edit mode.
        ...clickOnEditAndWaitEditMode(),
        ...openLinkPopup(":iframe .top_menu .nav-item a:contains('Home')", "Home"),
        {
            content: "Click on Edit Menu",
            trigger: ".o-we-linkpopover .js_edit_menu",
            run: "click",
        },
        {
            trigger: ".o_website_dialog:visible",
        },
        {
            content: "Trigger the link dialog (click 'Add Menu Item')",
            trigger: ".modal-body a:eq(0)",
            run: "click",
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_website_dialog input:eq(0)",
        },
        {
            content: "Confirm the new menu entry without a label",
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Continue)",
            run: "click",
        },
        {
            content: "It didn't save without a label. Fill label input.",
            trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_website_dialog input:eq(0)",
            run: "edit Random!",
        },
        {
            content: "Remove the URL input value",
            trigger:
                ".modal:not(.o_inactive_modal) .modal-dialog .o_website_dialog input#url_input",
            run: "edit ",
        },
        {
            content: "Confirm the new menu entry without a url",
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Continue)",
            run: "click",
        },
        {
            content: "Re-open the link dialog ",
            trigger: '.modal .input-group:has(.js_menu_label:contains("Random!")) .js_edit_menu',
            run: "click",
        },
        {
            content: "Check that the URL is #",
            trigger: ".modal:not(.o_inactive_modal) #url_input:value('#')",
        },
        {
            content: "Save the dialog",
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Continue)",
            run: "click",
        },
        {
            trigger: '.oe_menu_editor .js_menu_label:contains("Random!")',
        },
        {
            content: "Save the website menu with the new entry",
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        // Edit the new menu item from the "edit link" popover button
        clickOnExtraMenuItem({}, true),
        ...openLinkPopup(":iframe .top_menu .nav-item a:contains('Random!')", "Random!"),
        {
            content: "navbar shouldn't have any zwnbsp and no o_link_in_selection class",
            trigger: ':iframe nav.navbar:not(:has(.o_link_in_selection)):not(:contains("\ufeff"))',
        },
        {
            content: "Click on Edit Link",
            trigger: ".o-we-linkpopover a.o_we_edit_link",
            run: "click",
        },
        {
            content: "Change the label",
            trigger: ".modal-dialog .o_website_dialog input:eq(0)",
            run: "edit Modnar",
        },
        {
            content: "Confirm the new label",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        ...clickOnSave(),
        clickOnExtraMenuItem({}, true),
        {
            content: "Label should have changed",
            trigger: ':iframe .top_menu .nav-item a:contains("Modnar")',
        },
        // Edit the menu item from the "edit menu" popover button
        ...clickOnEditAndWaitEditMode(),
        clickOnExtraMenuItem({}, true),
        {
            content: "Wait for the builder sidebar to fully open",
            trigger: ":iframe .editor_enable",
            run: async function () {
                // Entering the edit mode opens the builder sidebar, which triggers
                // multiple iframe resize events, which in turn rebuilds the extra
                // menu items dropdown (see `auto_hide_menu.js` resize handler).
                //
                // We wait briefly to ensure all recalculations complete,
                // avoiding race conditions when opening the link popover.
                //
                // NOTE: the delay below (200ms) matches the CSS `transition-delay`
                // defined for `o-website-builder_sidebar`.
                await delay(200);
            },
        },
        ...openLinkPopup(":iframe .top_menu .nav-item a:contains('Modnar')", "Modnar"),
        {
            content: "Click on the popover Edit Menu button",
            trigger: ".o-we-linkpopover .js_edit_menu",
            run: "click",
        },
        {
            content: "Click on the dialog Edit Menu button",
            trigger: '.oe_menu_editor .js_menu_label:contains("Modnar")',
            run() {
                const liEl = this.anchor.closest("[data-menu-id]");
                liEl.querySelector("button.js_edit_menu").click();
            },
        },
        {
            content: "Change the label",
            trigger: ".modal:not(.o_inactive_modal) .modal-dialog .o_website_dialog input:eq(0)",
            run: "edit Modnar !!",
        },
        {
            content: "Confirm the new menu label",
            trigger: ".modal:not(.o_inactive_modal) .modal-footer button:contains(Continue)",
            run: "click",
        },
        {
            trigger: '.oe_menu_editor .js_menu_label:contains("Modnar !!")',
        },
        {
            content: "Save the website menu with the new menu label",
            trigger: ".modal:not(.o_inactive_modal) .modal-footer button:contains(save)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.oe_menu_editor))",
        },
        // Drag a block to be able to scroll later.
        goBackToBlocks(),
        ...insertSnippet({ id: "s_media_list", name: "Media List", groupName: "Content" }),
        ...clickOnSave(),
        clickOnExtraMenuItem({}, true),
        {
            content: "Label should have changed",
            trigger: ':iframe .top_menu .nav-item a:contains("Modnar !!")',
        },
        // Nest menu item from the menu.
        {
            content: "open site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "Click on Edit Menu",
            trigger: 'a[data-menu-xmlid="website.menu_edit_menu"]',
            run: "click",
        },
        {
            content: `Drag "Contact Us" menu below "Home" menu`,
            trigger: '.oe_menu_editor li:contains("Contact us") .oi-draggable',
            run(helpers) {
                return helpers.drag_and_drop('.oe_menu_editor li:contains("Home")', {
                    position: {
                        top: 57,
                        left: 5,
                    },
                    relative: true,
                });
            },
        },
        {
            content: "Drag 'Contact Us' item as a child of the 'Home' item",
            trigger: '.oe_menu_editor li:contains("Contact us") .oi-draggable',
            run: 'drag_and_drop .oe_menu_editor li:contains("Contact us") .form-control',
        },
        {
            content: "Wait for drop",
            trigger: '.oe_menu_editor li:contains("Home") ul li:contains("Contact us")',
        },
        // Drag the Mega menu to the first position.
        {
            content: "Drag Mega at the top",
            trigger: '.oe_menu_editor li:contains("Megaaaaa!") .oi-draggable',
            run(helpers) {
                return helpers.drag_and_drop('.oe_menu_editor li:contains("Home") .oi-draggable', {
                    position: {
                        top: 20,
                    },
                    relative: true,
                });
            },
        },
        {
            content: "Wait for drop",
            trigger: '.oe_menu_editor:first-child:contains("Megaaaaa!")',
        },
        {
            content: "Save the website menu with new nested menus",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Menu item should have a child",
            trigger: ':iframe .top_menu .nav-item a.dropdown-toggle:contains("Home")',
            run: "click",
        },
        // Check that with the auto close of dropdown menus, the dropdowns remain
        // openable.
        {
            content: "When menu item is opened, child item must appear in the shown menu",
            trigger:
                ':iframe .top_menu .nav-item:contains("Home") ul.show li a.dropdown-item:contains("Contact us")[href="/contactus"]',
            run() {
                // Scroll down.
                this.anchor
                    .closest("body")
                    .querySelector(".o_footer_copyright_name")
                    .scrollIntoView({ block: "start", inline: "nearest", behavior: "smooth" });
            },
        },
        {
            content: "The Home menu should be closed",
            trigger: ':iframe .top_menu .nav-item:contains("Home"):has(ul:not(.show))',
        },
        {
            content: "Open the Home menu after scroll",
            trigger: ':iframe .top_menu .nav-item a.dropdown-toggle:contains("Home")',
            async run(helpers) {
                await delay(1000);
                await helpers.click();
            },
        },
        {
            content: "Check that the Home menu is opened",
            trigger:
                ':iframe .top_menu .nav-item:contains("Home") ul.show li' +
                ' a.dropdown-item:contains("Contact us")[href="/contactus"]',
        },
        {
            content: "Close the Home menu",
            trigger: ':iframe .top_menu .nav-item:has(a.dropdown-toggle:contains("Home"))',
            run: "click",
        },
        {
            content: "Check that the Home menu is closed",
            trigger: ':iframe .top_menu .nav-item:contains("Home"):has(ul:not(.show))',
        },
        {
            content: "Open the mega menu",
            trigger: ':iframe .top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa!")',
            run: "click",
        },
        {
            content: "When the mega menu is opened, scroll up",
            trigger: ":iframe .top_menu .o_mega_menu_toggle.show",
            run() {
                const marginTopOfMegaMenu = getComputedStyle(
                    this.anchor.closest(".dropdown").querySelector(".o_mega_menu")
                )["margin-top"];
                if (marginTopOfMegaMenu !== "0px") {
                    console.error("The margin-top of the mega menu should be 0px");
                }
                // Scroll up.
                this.anchor
                    .closest("body")
                    .querySelector(".s_media_list_item:nth-child(2)")
                    .scrollIntoView(true);
            },
        },
        {
            content: "Check that the mega menu is closed",
            trigger:
                ':iframe .top_menu .nav-item:contains("Megaaaaa!"):has(div[data-name="Mega Menu"]:not(.show))',
        },
        {
            content: "Open the mega menu after scroll",
            trigger: ':iframe .top_menu .nav-item a.o_mega_menu_toggle:contains("Megaaaaa!")',
            run: "click",
        },
        {
            content: "Check that the mega menu is opened",
            trigger:
                ':iframe .top_menu .nav-item:has(a.o_mega_menu_toggle:contains("Megaaaaa!")) ' +
                ".s_mega_menu_odoo_menu",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            trigger: ":iframe main section.s_media_list .s_media_list_item:eq(2) h3:contains(post)",
        },
        {
            content: "Open nested menu item",
            trigger:
                ':iframe .o_top_fixed_element .nav-item:contains("Home"):nth-child(2) .dropdown-toggle',
            run: "click",
        },
        {
            // If this step fails, it means that a patch inside bootstrap was lost.
            content: "Press the 'down arrow' key.",
            trigger: ':iframe .top_menu .nav-item:contains("Home") li:contains("Contact us")',
            run: "press ArrowDown",
        },
        ...clickOnSave(),
        // Nest and re-arrange menu items for a newly created menu
        {
            content: "Open site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "Click on Edit Menu",
            trigger: 'a[data-menu-xmlid="website.menu_edit_menu"]',
            run: "click",
        },
        {
            content: "Trigger link dialog (click 'Add Menu Item')",
            trigger: ".modal-body a:eq(0)",
            run: "click",
        },
        {
            content: "Write a label for the new menu item",
            trigger: ".modal-dialog .o_website_dialog input:eq(0)",
            run: "edit new_menu",
        },
        {
            content: "Write a url for the new menu item",
            trigger: ".modal-dialog .o_website_dialog input:eq(1)",
            run: "edit #",
        },
        {
            content: "Confirm the new menu entry",
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Continue)",
            run: "click",
        },
        {
            content: "Check if new menu(new_menu) is added",
            trigger: '.oe_menu_editor li:contains("new_menu")',
        },
        {
            content: "Trigger link dialog (click 'Add Menu Item')",
            trigger: ".modal-body a:eq(0)",
            run: "click",
        },
        {
            content: "Write a label for the new menu item",
            trigger: ".modal-dialog .o_website_dialog input:eq(0)",
            run: "edit new_nested_menu",
        },
        {
            content: "Write a url for the new menu item",
            trigger: ".modal-dialog .o_website_dialog input:eq(1)",
            run: "edit #",
        },
        {
            content: "Confirm the new menu entry",
            trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains(Continue)",
            run: "click",
        },
        {
            content: "Check if new menu(new_nested_menu) is added",
            trigger: '.oe_menu_editor li:contains("new_nested_menu")',
        },
        {
            content: "Nest 'new_nested_menu' under 'new_menu'",
            trigger: '.oe_menu_editor li:contains("new_nested_menu") .oi-draggable',
            run: "drag_and_drop .oe_menu_editor li:contains('new_menu') .form-control",
        },
        {
            content: "Drag 'Modnar !!' below 'new_menu'",
            trigger: '.oe_menu_editor li:contains("Modnar !!") .oi-draggable',
            async run(helpers) {
                await helpers.drag_and_drop(
                    '.oe_menu_editor li:contains("new_menu") .oi-draggable',
                    {
                        position: "bottom",
                    }
                );
            },
        },
        {
            content: "Nest 'Modnar !!' under 'new_menu'",
            trigger: '.oe_menu_editor li:contains("Modnar !!") .oi-draggable',
            run: "drag_and_drop .oe_menu_editor li:contains('new_menu') .form-control",
        },
        {
            content: "Check if 'nested_menu' and 'Modnar !!' is nested under 'new_menu'",
            trigger:
                '.oe_menu_editor li:contains("new_menu") > ul > li:contains("Modnar !!") + li:contains("nested_menu")',
        },
        {
            content: "Move 'Modnar !!' below 'new_nested_menu' inside the 'new_menu'",
            trigger:
                '.oe_menu_editor  li:contains("new_menu") > ul > li:contains("Modnar !!") .oi-draggable',
            async run(helpers) {
                await helpers.drag_and_drop(
                    ".oe_menu_editor  li:contains('new_menu') > ul > li:contains('new_nested_menu') .oi-draggable",
                    {
                        position: "bottom",
                    }
                );
            },
        },
        {
            content: "Check if 'Modnar !!' is now below 'new_nested_menu' in 'new_menu'",
            trigger:
                '.oe_menu_editor li:contains("new_menu") > ul > li:last-child:contains("Modnar !!")',
        },
    ]
);

registerWebsitePreviewTour(
    "edit_menus_delete_parent",
    {
        url: "/",
    },
    () => [
        {
            trigger: ":iframe #wrapwrap",
        },
        {
            content: "Open site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "Click on Edit Menu",
            trigger: 'a[data-menu-xmlid="website.menu_edit_menu"]',
            run: "click",
        },
        {
            content: "Delete Home menu",
            trigger: ".modal-body ul li:nth-child(1) button.js_delete_menu",
            run: "click",
        },
        {
            content: "Save",
            trigger: ".modal-footer button:first-child",
            run: "click",
        },
    ]
);
