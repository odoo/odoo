import {
    changeOptionInPopover,
    clickOnExtraMenuItem,
    clickOnSave,
    openLinkPopup,
    registerWebsitePreviewTour,
    clickToolbarButton,
} from "@website/js/tours/tour_utils";

const toggleMegaMenu = (stepOptions) =>
    Object.assign(
        {},
        {
            content: "Toggles the mega menu.",
            trigger: ":iframe .top_menu .nav-item a.o_mega_menu_toggle",
            run(helpers) {
                // If the mega menu is displayed inside the extra menu items, it should
                // already be displayed.
                if (!this.anchor.closest(".o_extra_menu_items")) {
                    helpers.click();
                }
            },
        },
        stepOptions
    );

registerWebsitePreviewTour(
    "edit_megamenu",
    {
        url: "/",
        edition: true,
    },
    () => [
        // Add a megamenu item to the top menu.
        {
            content: "Click on a menu item",
            trigger: ":iframe .top_menu .nav-item .nav-link [data-oe-model='website.menu']",
            run: "click",
        },
        {
            content: "Click on 'Link' to open Link Dialog",
            trigger: ".o-we-linkpopover .js_edit_menu",
            run: "click",
        },
        {
            trigger: ".o_website_dialog:visible",
        },
        {
            content: "Trigger the link dialog (click 'Add Mega Menu Item')",
            trigger: ".modal-body a:eq(1)",
            run: "click",
        },
        {
            content: "Write a label for the new menu item",
            trigger: ".modal-dialog .o_website_dialog input",
            run: "edit Megaaaaa!",
        },
        {
            content: "Confirm the mega menu label",
            trigger: ".modal .modal-footer button:contains(Continue)",
            run: "click",
        },
        {
            trigger:
                '.oe_menu_editor [data-is-mega-menu="true"] .js_menu_label:contains("Megaaaaa!")',
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
            trigger: ".o_builder_sidebar_open",
        },
        {
            trigger: ".o_builder_open .o_website_preview:not(.o_is_blocked)",
        },
        // Edit a menu item
        clickOnExtraMenuItem({}, true),
        toggleMegaMenu({}),
        {
            content: "Select the last menu link of the first column",
            trigger: ":iframe .s_mega_menu_odoo_menu .row > div:first-child .nav > :nth-child(6)", // 6th is the last one
            run: "click",
        },
        {
            content: "Hit the delete button to remove the menu link",
            trigger: ".o_overlay_options .oe_snippet_remove",
            run: "click",
        },
        {
            content: "Check that the last menu link was deleted",
            trigger:
                ":iframe .s_mega_menu_odoo_menu .row > div:first-child .nav:not(:has(:nth-child(6)))",
        },
        {
            content: "Click on the first title item.",
            trigger: ":iframe .o_mega_menu h4",
            run: "click",
        },
        {
            content: "Press enter.",
            trigger: ":iframe .o_mega_menu h4",
            run() {
                this.anchor.dispatchEvent(
                    new window.InputEvent("input", { bubbles: true, inputType: "insertParagraph" })
                );
            },
        },
        {
            content: "The menu should still be visible. Edit a menu item.",
            trigger: ":iframe .o_mega_menu h4",
            // The content is removed in the previous step so it's now invisible.
            run: "editor New Menu Item",
        },
        {
            // If this step fails, it means that a patch inside bootstrap was lost.
            content: "Press the 'down arrow' key.",
            trigger: ":iframe .o_mega_menu h4",
            run: "press ArrowDown",
        },
        ...clickOnSave(),
        clickOnExtraMenuItem({}, true),
        toggleMegaMenu(),
        {
            content: "The menu item should have been renamed.",
            trigger: ':iframe .o_mega_menu h4:contains("New Menu Item")',
        },
    ]
);
registerWebsitePreviewTour(
    "megamenu_active_nav_link",
    {
        url: "/",
        edition: true,
    },
    () => [
        // Add a megamenu item to the top menu.
        ...openLinkPopup(":iframe .top_menu .nav-item a:contains('Home')", "Home"),
        {
            content: "Click on 'Link' to open Link Dialog",
            trigger: ".o-we-linkpopover button.js_edit_menu",
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
            trigger: ".modal .modal-footer .btn-primary:contains(Continue)",
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
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "Check for the new mega menu",
            trigger: `:iframe .top_menu:has(.nav-item a.o_mega_menu_toggle:contains("Megatron"))`,
        },
        clickOnExtraMenuItem({}, true),
        toggleMegaMenu({}),
        ...openLinkPopup(":iframe .s_mega_menu_odoo_menu .nav-link:contains('Laptops')", "Laptops"),
        {
            content: "Click on 'Edit Link'",
            trigger: ".o-we-linkpopover a.o_we_edit_link",
            run: "click",
        },
        {
            content: "Change the link",
            trigger: ".o-we-linkpopover input.o_we_href_input_link",
            run: "edit /new_page",
        },
        ...clickOnSave(),
        clickOnExtraMenuItem({}, true),
        toggleMegaMenu(),
        {
            content: "Click on the first menu link of the first column",
            trigger: ":iframe .s_mega_menu_odoo_menu .row > div:first-child .nav > :nth-child(1)",
            run: "click",
        },
        {
            content: "Check if the new mega menu is active",
            trigger: `:iframe .top_menu:has(.nav-item a.o_mega_menu_toggle.active:contains("MegaTron"))`,
        },
    ]
);
registerWebsitePreviewTour(
    "edit_megamenu_big_icons_subtitles",
    {
        url: "/",
        edition: true,
    },
    () => [
        // Add a megamenu item to the top menu.
        ...openLinkPopup(":iframe .top_menu .nav-item a", "Home"),
        {
            content: "Click on 'Link' to open Link Dialog",
            trigger: ".o-we-linkpopover .js_edit_menu",
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
            run: "edit Megaaaaa2!",
        },
        {
            content: "Confirm the mega menu label",
            trigger: ".modal .modal-footer .btn-primary:contains(Continue)",
            run: "click",
        },
        {
            trigger:
                '.oe_menu_editor [data-is-mega-menu="true"] .js_menu_label:contains("Megaaaaa2!")',
        },
        {
            content: "Save the website menu with a new mega menu",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "Check for the new mega menu",
            trigger: ':iframe .top_menu:has(.nav-item a.o_mega_menu_toggle:contains("Megaaaaa2!"))',
        },
        // Edit a menu item
        clickOnExtraMenuItem({}, true),
        toggleMegaMenu({}),
        {
            content: "Select the first menu link of the first column",
            trigger: ":iframe .s_mega_menu_odoo_menu .row > div:first-child .nav > :first-child",
            run: "click",
        },
        // Change MegaMenu template
        ...changeOptionInPopover("Mega Menu", "Template", "[title='Big Icons Subtitles']"),
        ...clickToolbarButton(
            "h4 of first menu link of the first column",
            ".s_mega_menu_big_icons_subtitles .row > div:first-child .nav > :first-child h4",
            "Toggle bold"
        ),
        ...clickOnSave(),
        clickOnExtraMenuItem({}, true),
        toggleMegaMenu(),
        {
            content: "The menu item should only convert selected text to Bold.",
            trigger:
                ":iframe .s_mega_menu_big_icons_subtitles .row > div:first-child .nav > :first-child span:not(:has(strong))",
        },
    ]
);
