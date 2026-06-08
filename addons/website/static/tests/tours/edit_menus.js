/** @odoo-module */

import { registry } from "@web/core/registry";
import {
    clickOnEditAndWaitEditMode,
    clickOnExtraMenuItem,
    clickOnSave,
    goBackToBlocks,
    insertSnippet,
    openLinkPopup,
} from "@website/js/tours/tour_utils";

export const triggerModalEditMenu = `.modal:has(.modal-title:contains(edit menu))`;
const triggerModalMegaMenuItem = `.modal:has(.modal-title:contains(mega menu item))`;
const triggerModalMenuItem = `.modal:has(.modal-title:contains(menu item))`;

const menuEditorLi = (title, isMegaMenu = false) =>
    `${triggerModalEditMenu} .oe_menu_editor li${
        isMegaMenu ? `[data-is-mega-menu="true"]` : ``
    }:has(.js_menu_label:contains(${title}))`;

export const addMegaMenu = (title) => {
    const steps = [
        {
            content: "Trigger the link dialog",
            trigger: `${triggerModalEditMenu} a:contains(Add Mega Menu Item)`,
            run: "click",
        },
        {
            content: "Write a label for the new menu item",
            trigger: `${triggerModalMegaMenuItem} input:first`,
            run: `edit ${title}`,
        },
        {
            content: "Confirm the mega menu label",
            trigger: `${triggerModalMegaMenuItem} button:contains(Continue)`,
            run: "click",
        },
        {
            trigger: menuEditorLi(title, true),
        },
        {
            content: "Save the new menu",
            trigger: `${triggerModalEditMenu} button.btn-primary:contains(Save)`,
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "Wait for the Megaaaaa! item to be added to the navbar after save",
            trigger: `:iframe .top_menu:has(a.o_mega_menu_toggle:contains(${title}))`,
        },
    ];
    return steps;
};

const openEditMenu = [
    {
        content: "Open site menu",
        trigger: '.o_navbar button[data-menu-xmlid="website.menu_site"]',
        run: "click",
    },
    {
        content: "Click on Edit Menu",
        trigger: '.o_popover a[data-menu-xmlid="website.menu_edit_menu"]',
        run: "click",
    },
];

export const editMenu = ({ title, href } = {}) => {
    const steps = [];
    if (title) {
        steps.push({
            content: "edit title value",
            trigger: `${triggerModalMenuItem} input:first`,
            run: `edit ${title}`,
        });
    }
    if (href) {
        steps.push({
            content: "edit link value",
            trigger: `${triggerModalMenuItem} #url_input`,
            run: `edit ${href}`,
        });
    }
    steps.push({
        content: "Save menu item",
        trigger: `${triggerModalMenuItem} button.btn-primary:contains(Continue)`,
        run: "click",
    });
    return steps;
};

const addMenu = (title, href = "#") => {
    const steps = [
        {
            content: "Trigger the link dialog",
            trigger: `${triggerModalEditMenu} a:contains(Add Menu Item)`,
            run: "click",
        },
        {
            content: "Confirm the new menu entry without a label",
            trigger: `${triggerModalMenuItem} button.btn-primary:contains(Continue)`,
            run: "click",
        },
        {
            content: "It didn't save without a label",
            trigger: `${triggerModalMenuItem}:has(input.is-invalid)`,
        },
        ...editMenu({ title, href }),
        {
            content: "Click on edit to re-edit the menu",
            trigger: `${menuEditorLi(title)} .js_edit_menu`,
            run: "click",
        },
        {
            content: `Check that the URL is ${href}`,
            trigger: `${triggerModalMenuItem} #url_input:value(${href})`,
        },
        {
            content: "Save menu item",
            trigger: `${triggerModalMenuItem} button.btn-primary:contains(Continue)`,
            run: "click",
        },
        {
            trigger: menuEditorLi(title),
        },
        {
            content: "Save the website menu with the new entry",
            trigger: `${triggerModalEditMenu} button.btn-primary:contains(save)`,
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "Check Random! has been added to top menu",
            trigger: `:iframe .top_menu:has(a:contains(${title}))`,
        },
    ];
    return steps;
};

/**
 * Generates tour steps that add 5 extra menu items ("brol 1" … "brol 5") to
 * the website navbar via the menu editor dialog.
 *
 * On a fresh localhost install only a handful of menus exist, so the navbar
 * always has enough space to display them inline. On runbot (or any install
 * with many addons), the navbar overflows and the surplus items are collapsed
 * into the "extra menu" dropdown (.o_extra_menu_items). Mega-menu tour steps
 * that rely on clickOnExtraMenuItem only work when that dropdown is present,
 * so this helper artificially inflates the menu list to reproduce runbot-like
 * conditions locally.
 */
export const simulateLotOfMenusAsOnRunbot = [1, 2, 3, 4, 5].flatMap((i) => [
    {
        content: `Add menu item: brol ${i}`,
        trigger: `${triggerModalEditMenu} a:contains(add menu item)`,
        run: "click",
    },
    ...editMenu({ title: `brol ${i}` }),
]);

registry.category("web_tour.tours").add("parent_child_menu", {
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
            trigger: "div[name='child_id'] td.o_field_x2many_list_row_add button",
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
            trigger: "body:has(.o_form_dirty) .o_form_button_save",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o_form_dirty))",
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

registry.category("web_tour.tours").add("edit_menus", {
    steps: () => [
        // Add a megamenu item from the menu.
        {
            trigger: ":iframe #wrapwrap",
        },
        ...openEditMenu,
        ...simulateLotOfMenusAsOnRunbot,
        ...addMegaMenu("Megaaaaa!"),
        // Add a menu item in edit mode.
        ...clickOnEditAndWaitEditMode(),
        ...openLinkPopup({
            trigger: ":iframe .top_menu .nav-item a:contains('Home')",
            label: "Home",
        }),
        {
            content: "Click on Edit Menu",
            trigger: ".o-we-linkpopover .js_edit_menu",
            run: "click",
        },
        // Add menu in nav to simulate more menus in localhost
        // (as on runbot when all addons are installed)
        ...addMenu("Random!"),
        // Edit the new menu item from the "edit link" popover button
        clickOnExtraMenuItem({}, true),
        {
            content: "navbar shouldn't have any zwnbsp and no o_link_in_selection class",
            trigger: ':iframe nav.navbar:not(:has(.o_link_in_selection)):not(:contains("\ufeff"))',
        },
        ...openLinkPopup({
            trigger: ":iframe .top_menu .nav-item a:contains('Random!')",
            label: "Home",
            url: "/#",
            edit: true,
        }),
        ...editMenu({ title: "Modnar" }),
        ...clickOnSave(),
        clickOnExtraMenuItem({}, true),
        {
            content: "Label should have changed",
            trigger: ':iframe .top_menu .nav-item a:contains("Modnar")',
        },
        // Edit the menu item from the "edit menu" popover button
        ...clickOnEditAndWaitEditMode(),
        clickOnExtraMenuItem({}, true),
        ...openLinkPopup({
            trigger: ":iframe .top_menu .nav-item a:contains('Modnar')",
            label: "Home",
            url: "/#",
        }),
        {
            content: "Click on the popover Edit Menu button",
            trigger: ".o-we-linkpopover .js_edit_menu",
            run: "click",
        },
        {
            content: "Click on the dialog Edit Menu button",
            trigger: `${menuEditorLi("Modnar")} .js_edit_menu`,
            run: "click",
        },
        ...editMenu({ title: "Modnar !!" }),
        {
            trigger: `${menuEditorLi("Modnar !!")}`,
        },
        {
            content: "Save the website menu with the new menu label",
            trigger: `${triggerModalEditMenu} button:contains(save)`,
            run: "click",
        },
        {
            trigger: "body:not(:has(.oe_menu_editor)):not(.modal-open)",
        },
        {
            trigger:
                ".o-website-builder_sidebar:has([aria-selected]:contains(Style)) .o-tab-content:contains(Select a block on your page to style it.)",
        },
        goBackToBlocks(),
        ...insertSnippet({ id: "s_media_list", name: "Media List", groupName: "Content" }),
        ...clickOnSave(),
        clickOnExtraMenuItem({}, true),
        {
            content: "Label should have changed",
            trigger: ':iframe .top_menu .nav-item a:contains("Modnar !!")',
        },
        {
            content: "Click on the extra menu dropdown toggle if it is there to close it",
            trigger: ":iframe .top_menu",
            async run(actions) {
                // Note: the button might not exist (it only appear if there is
                // many menu items).
                const extraMenuButtonEl = this.anchor.querySelector(
                    ".o_extra_menu_items a.nav-link"
                );
                // Don't click on the extra menu button if it's already hidden
                if (extraMenuButtonEl && extraMenuButtonEl.classList.contains("show")) {
                    const dropdownFullyClosed = Promise.withResolvers();
                    extraMenuButtonEl.addEventListener(
                        "hidden.bs.dropdown",
                        dropdownFullyClosed.resolve,
                        { once: true }
                    );
                    await actions.click(extraMenuButtonEl);
                    await dropdownFullyClosed.promise;
                }
            },
        },
        // Nest menu item from the menu.
        ...openEditMenu,
        {
            content: `Drag "Modnar !!" menu below "Home" menu`,
            trigger: '.oe_menu_editor li:contains("Modnar !!") .oi-draggable',
            async run({ drag_and_drop }) {
                await drag_and_drop('.oe_menu_editor li:contains("Home")', {
                    position: {
                        top: 57,
                        left: 5,
                    },
                    relative: true,
                });
            },
        },
        {
            content: "Drag 'Modnar !!' item as a child of the 'Home' item",
            trigger: '.oe_menu_editor li:contains("Modnar !!") .oi-draggable',
            run: 'drag_and_drop .oe_menu_editor li:contains("Modnar !!") .form-control',
        },
        {
            content: "Wait for drop",
            trigger: '.oe_menu_editor li:contains("Home") ul li:contains("Modnar !!")',
        },
        // Drag the Mega menu to the first position.
        {
            content: "Drag Mega at the top",
            trigger: '.oe_menu_editor li:contains("Megaaaaa!") .oi-draggable',
            async run({ drag_and_drop }) {
                await drag_and_drop('.oe_menu_editor li:contains("Home") .oi-draggable', {
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
                ':iframe .top_menu .nav-item:contains("Home") ul.show li a.dropdown-item:contains("Modnar !!")',
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
            run: "click",
        },
        {
            content: "Check that the Home menu is opened",
            trigger:
                ':iframe .top_menu .nav-item:contains("Home") ul.show li' +
                ' a.dropdown-item:contains("Modnar !!")',
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
            trigger: ':iframe .top_menu .nav-item:contains("Home") li:contains("Modnar !!")',
            run: "press ArrowDown",
        },
        ...clickOnSave(),
        // Nest and re-arrange menu items for a newly created menu
        ...openEditMenu,
        ...addMenu("new_menu"),
        ...openEditMenu,
        ...addMenu("new_nested_menu"),
        ...openEditMenu,
        // Remove simulateLotOfMenusAsOnRunbot
        ...[1, 2, 3, 4, 5].map((i) => ({
            content: `Delete Brol ${i}`,
            trigger: `${menuEditorLi(`brol ${i}`)} .js_delete_menu`,
            run: "click",
        })),
        {
            content: "Nest 'new_nested_menu' under 'new_menu'",
            trigger: '.oe_menu_editor li:contains("new_nested_menu") .oi-draggable',
            async run({ drag_and_drop }) {
                await drag_and_drop(".oe_menu_editor li:contains('new_menu') .form-control", {
                    position: "bottom",
                });
            },
        },
        {
            content: "Drag 'Modnar !!' below 'new_menu'",
            trigger:
                '.oe_menu_editor li:contains("Home") > ul > li:contains("Modnar !!") .oi-draggable',
            async run({ drag_and_drop }) {
                await drag_and_drop('.oe_menu_editor li:contains("new_menu") .oi-draggable', {
                    position: "bottom",
                });
            },
        },
        {
            content: "Nest 'Modnar !!' under 'new_menu'",
            trigger: '.oe_menu_editor li:contains("Modnar !!") .oi-draggable',
            async run({ drag_and_drop }) {
                await drag_and_drop(
                    ".oe_menu_editor li:contains('new_menu') > ul > li:contains('new_nested_menu')",
                    {
                        position: "top",
                    }
                );
            },
        },
        {
            content: "Check if 'new_nested_menu' and 'Modnar !!' is nested under 'new_menu'",
            trigger:
                '.oe_menu_editor li:contains("new_menu") > ul > li:contains("Modnar !!") + li:contains("new_nested_menu")',
        },
        {
            content: "Move 'Modnar !!' below 'new_nested_menu' inside the 'new_menu'",
            trigger:
                '.oe_menu_editor  li:contains("new_menu") > ul > li:contains("Modnar !!") .oi-draggable',
            async run({ drag_and_drop }) {
                await drag_and_drop(
                    ".oe_menu_editor li:contains('new_menu') > ul > li:contains('new_nested_menu') .oi-draggable",
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
    ],
});

registry.category("web_tour.tours").add("edit_menus_delete_parent", {
    steps: () => [
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
    ],
});
