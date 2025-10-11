import {
    changeColor,
    clickOnSave,
    clickOnSnippet,
    registerWebsitePreviewTour,
    clickOnEditAndWaitEditMode,
} from "@website/js/tours/tour_utils";

/**
 * Helper function to create a new page
 * @param {string} pageName - Name of the page to create
 */
function createNewPage(pageName) {
    return [
        {
            content: `Open new page menu for ${pageName}`,
            trigger: ".o_menu_systray .o_new_content_container button",
            run: "click",
        },
        {
            content: `Click on new page for ${pageName}`,
            trigger: "button.o_new_content_element",
            run: "click",
        },
        {
            content: "Click on Use this template",
            trigger: ".o_page_template .o_button_area:not(:visible)",
            run: "click",
        },
        {
            content: "Insert page name",
            trigger: '.modal .modal-dialog .modal-body input[type="text"]',
            run: `edit ${pageName}`,
        },
        {
            content: "Check that the page name is entered",
            trigger: `input[type="text"]:value(${pageName})`,
        },
        {
            content: "Create page",
            trigger: ".modal button.btn-primary:contains(create)",
            run: "click",
        },
        {
            content: "Wait for the modal to disappear",
            trigger: "body:not(:has(.modal))",
        },
        ...clickOnSave(),
    ];
}

/**
 * Helper function to verify color in header and dropdown or sub menu
 * @param {string} menuSelector - Selector for the dropdown menu container
 */
function verifyColor(menuSelector) {
    return [
        {
            content: "Check that both background and text colors match with the dropdown menu",
            trigger: ":iframe #wrapwrap header .navbar",
            run() {
                const navbarEl = this.anchor;
                const menuEl = navbarEl.querySelector(menuSelector);
                if (!menuEl) {
                    throw new Error(`Menu element not found for selector: ${menuSelector}`);
                }
                const navbarBg = getComputedStyle(navbarEl).backgroundColor;
                const menuBg = getComputedStyle(menuEl).backgroundColor;
                const navbarTextColor = getComputedStyle(
                    navbarEl.querySelector(".top_menu li:first-child a span")
                ).color;
                const menuTextSelector = `${menuSelector} li a`;
                const menuTextColor = getComputedStyle(
                    navbarEl.querySelector(menuTextSelector)
                ).color;
                if (navbarBg !== menuBg) {
                    throw new Error(
                        `Background color mismatch: navbar=${navbarBg}, menu=${menuBg}`
                    );
                }
                if (navbarTextColor !== menuTextColor) {
                    throw new Error(
                        `Text color mismatch: navbar=${navbarTextColor}, menu=${menuTextColor}`
                    );
                }
            },
        },
    ];
}

registerWebsitePreviewTour(
    "header_color_related_issue",
    {
        url: "/",
    },
    () => [
        ...createNewPage("Test1"),
        ...createNewPage(
            "abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnopqrstuvwxyz1234567890"
        ),
        {
            content: "Open site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "Click on edit menu",
            trigger: 'a[data-menu-xmlid="website.menu_edit_menu"]',
            run: "click",
        },
        {
            content: "Drag Test1 menu below Home menu",
            trigger: '.oe_menu_editor li:contains("Test1") .oi-draggable',
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
            content: "Drag 'Test1' item as a child of the 'Home' item",
            trigger: '.oe_menu_editor li:contains("Test1") .oi-draggable',
            run: 'drag_and_drop .oe_menu_editor li:contains("Test1") .form-control',
        },
        {
            content: "Wait for drop",
            trigger: '.oe_menu_editor li:contains("Home") ul li:contains("Test1")',
        },
        {
            content: "Click on save button",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Wait for the edit menu dialog to close",
            trigger: ":iframe :not([id='dialog_1'])",
        },
        {
            content: "Wait for the page to load",
            trigger: ":iframe #wrapwrap",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet({ id: "o_header_standard", name: "Header" }),
        ...changeColor({
            containerTitle: "Header",
            optionLabel: "Background",
            colorTabsWrapperSelector: ".o-hb-colorpicker",
            colorTabSelector: ".custom-tab",
            colorSelector: "data-color='600'",
        }),
        ...changeColor({
            containerTitle: "Header",
            optionLabel: "Format",
            colorTabsWrapperSelector: ".o-hb-colorpicker",
            colorTabSelector: ".custom-tab",
            colorSelector: "data-color='200'",
        }),
        ...clickOnSave(),
        {
            content: "Click on the + menu in header",
            trigger: ":iframe #wrapwrap header .navbar .o_extra_menu_items a",
            run: "click",
        },
        ...verifyColor(".o_extra_menu_items .dropdown-menu"),
        {
            content: "Click on the Test1 to open submenu",
            trigger: ":iframe #wrapwrap .navbar li:first-child a",
            run: "click",
        },
        {
            content: "Wait for submenu to open",
            trigger: ":iframe #wrapwrap .navbar li:first-child .show",
        },
        ...verifyColor("li:first-child .dropdown-menu"),
    ]
);
