import {
    clickOnSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("create_missing_page", {
    url: "/",
    edition: true,
}, () => [
    ...clickOnSnippet({id: "o_header_standard", name: "Header"}),
    {
        content: "Click the 'Menu Editor' button in the header options",
        trigger: ".o_we_customize_panel we-button[data-open-menu-editor]",
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
        run: "edit Zoé’s Diner",
    },
    {
        content: "Clear the 'url' input",
        trigger: ".modal-dialog .o_website_dialog input:eq(1)",
        run: "clear",
    },
    {
        content: "Check if the 'url' input placeholder is correctly slugified.",
        trigger: ".modal-dialog .o_website_dialog input:eq(1)[placeholder='zoe-s-diner']",
    },
    {
        content: "Edit the 'url' input",
        trigger: ".modal-dialog .o_website_dialog input:eq(1)",
        run: "edit /contactus",
    },
    {
        content: "Check whether the page is found.",
        trigger: ".modal-dialog .o_website_dialog main div.position-relative:not(.o_page_not_found)",
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
        trigger: ".modal-dialog .o_website_dialog .modal-footer .btn-primary:contains(Continue)",
        run: "click",
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
    ...clickOnSnippet({id: "o_header_standard", name: "Header"}),
    {
        content: "Click the 'Menu Editor' button in the header options",
        trigger: ".o_we_customize_panel we-button[data-open-menu-editor]",
        run: "click",
    },
    {
        content: "Check that the 'Create Page' button is missing.",
        trigger: ".oe_menu_editor .js_menu_label:contains('Zoé’s Diner')",
        run() {
            if (this.anchor.closest(".form-control")
                    .querySelector("button")
                    ?.textContent.includes('Create Page')) {
                throw new Error("The 'Create Page' button should be missing");
            }
        },
    },
    // Drag the new menu item to the first position. If this is not done, the
    // tour fails when the new menu is in the extra menu.
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
]);
