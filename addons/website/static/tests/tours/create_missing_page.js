import {
    clickOnSnippet,
    registerWebsitePreviewTour,
    changeOption,
    clickOnSave,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "create_missing_page",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...clickOnSnippet({ id: "o_header_standard", name: "Header" }),
        changeOption("Header", "[aria-label='Open menu editor']"),
        {
            content: "Open the link dialog (click 'Add Menu Item')",
            trigger: ".modal-body a:eq(0)",
            run: "click",
        },
        {
            content: "Edit the 'Menu Title' input",
            trigger: ".modal-dialog .o_website_dialog input:eq(0)",
            run: "edit Zoé’s Diner",
        },
        {
            content: "Check if the 'url' input is correctly slugified.",
            trigger: ".modal-dialog .o_website_dialog input:eq(1):value('zoe-s-diner')",
        },
        {
            content: "Edit the 'url' input",
            trigger: ".modal-dialog .o_website_dialog input:eq(1)",
            run: "edit /contactus",
        },
        {
            content: "Check whether the page is found.",
            trigger:
                ".modal-dialog .o_website_dialog main div.position-relative:not(.o_page_not_found)",
        },
        {
            content: "Edit the 'url' input again",
            trigger: ".modal-dialog .o_website_dialog input:eq(1)",
            run: "edit zoe-s-diner",
        },
        {
            content: "Check that the page is not found.",
            trigger: ".modal-dialog .o_website_dialog main div.position-relative.o_page_not_found",
        },
        {
            content: "Confirm the new menu entry",
            trigger:
                ".modal-dialog .o_website_dialog .modal-footer .btn-primary:contains(Continue)",
            run: "click",
        },
        // Drag the new menu item to the first position. If this is not done,
        // the tour fails when the new menu is in the extra menu.
        {
            content: "Drag the new menu item at the top",
            trigger: '.oe_menu_editor li:contains("Zoé’s Diner") .oi-draggable',
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
            content: "Click on the 'Create Page' button",
            trigger: ".oe_menu_editor button:contains('Create Page')",
            run: "click",
        },
        {
            content: "Click on 'Blank Page'",
            trigger: ".o_page_template .o_button_area:not(:visible)",
            run: "click",
        },
        {
            content: "Wait to land on '/zoe-s-diner' page",
            trigger: ':iframe a[href="/zoe-s-diner"].nav-link.active',
        },
        {
            content: "Wait edit mode",
            trigger: ".o_builder_sidebar_open",
        },
        ...clickOnSnippet({ id: "o_header_standard", name: "Header" }),
        changeOption("Header", "[aria-label='Open menu editor']"),
        {
            content: "Check that the 'Create Page' button is missing.",
            trigger: ".oe_menu_editor .js_menu_label:contains('Zoé’s Diner')",
            run() {
                if (
                    this.anchor
                        .closest(".form-control")
                        .querySelector("button")
                        ?.textContent.includes("Create Page")
                ) {
                    throw new Error("The 'Create Page' button should be missing");
                }
            },
        },
        {
            content: "Save the menu",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Check that we are on the new page.",
            trigger: ":iframe a[href='/zoe-s-diner'].nav-link.active",
        },
        {
            content: "Check that it is not a 404 page.",
            trigger: ".o_website_preview:not([data-view-xmlid='website.page_404'])",
        },
        {
            content: "Check that the page title has been correctly set.",
            trigger: ':iframe head title:contains("Zoé’s Diner"):not(:visible)',
        },
        {
            content: "Click on the 'Zoé’s Diner' link.",
            trigger: ":iframe a[href='/zoe-s-diner'].nav-link.active span",
            run: "click",
        },
        {
            content: "Click Edit Menu in the popover.",
            trigger: ".o-we-linkpopover button.js_edit_menu",
            run: "click",
        },
        {
            content: "Open the link dialog (click 'Add Menu Item')",
            trigger: ".modal-body a:eq(0)",
            run: "click",
        },
        {
            content: "Edit the 'Menu Title' input",
            trigger: ".modal-dialog .o_website_dialog input:eq(0)",
            run: "edit The Sea Hotel",
        },
        {
            content: "Edit the 'url' input",
            trigger: ".modal-dialog .o_website_dialog input:eq(1)",
            run: "edit sea-hotel",
        },
        {
            content: "Confirm the new menu entry",
            trigger:
                ".modal-dialog .o_website_dialog .modal-footer .btn-primary:contains(Continue)",
            run: "click",
        },
        // Drag the new menu item to the first position. If this is not done,
        // the tour fails when the new menu is in the extra menu.
        {
            content: "Drag the new menu item at the top",
            trigger: '.oe_menu_editor li:contains("The Sea Hotel") .oi-draggable',
            run(helpers) {
                return helpers.drag_and_drop(
                    '.oe_menu_editor li:contains("Zoé’s Diner") .oi-draggable',
                    {
                        position: {
                            top: 20,
                        },
                        relative: true,
                    }
                );
            },
        },
        {
            content: "Save the menu",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Click on the 'The Sea Hotel' link.",
            trigger: ":iframe a[href='/sea-hotel'].nav-link",
            run: "click",
        },
        {
            content: "Click on the 'Create Page' alert button.",
            trigger: ".o_action_manager .alert a.btn",
            run: "click",
        },
        {
            content: "Click on 'Blank Page'",
            trigger: ".o_page_template .o_button_area:not(:visible)",
            run: "click",
        },
        {
            content: "Wait edit mode",
            trigger: ".o_builder_sidebar_open",
        },
        {
            content: "Wait to land on '/sea-hotel' page",
            trigger: ':iframe a[href="/sea-hotel"].nav-link.active',
        },
    ]
);
