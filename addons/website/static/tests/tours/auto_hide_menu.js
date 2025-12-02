import {
    clickOnEditAndWaitEditMode,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

let numNavChildren;

const addNavItem = [
    {
        content: "Add a menu item",
        trigger: ".modal-dialog .fa-plus-circle:first-child",
        run: "click",
    },
    {
        content: "Input name",
        trigger: ".o_menu_dialog_form input",
        run: "edit name",
    },
    {
        content: "Click Continue",
        trigger: ".modal-dialog .modal-footer .btn-primary:contains(Continue)",
        run: "click",
    },
];

const getTheLayoutChildren = {
    content: "Get the number of elements in the navbar",
    trigger: ":iframe #o_main_nav ul[role='menu']",
    async run() {
        numNavChildren = this.anchor.children.length;
    },
};

const checkThatLayoutChanged = {
    content: "Ensure that the navbar layout has changed",
    trigger: ":iframe #o_main_nav ul[role='menu']",
    async run() {
        if (this.anchor.children.length === numNavChildren) {
            throw new Error("Navbar layout should change");
        }
    },
};

registerWebsitePreviewTour(
    "website_auto_hide_menu",
    {
        url: "/",
    },
    () => [
        {
            content: "Click on Site",
            trigger: ".o_main_navbar .o_menu_sections :contains('Site')",
            run: "click",
        },
        {
            content: "Click on Menu Editor",
            trigger: ".o_popover .o-dropdown-item:contains('Menu Editor')",
            run: "click",
        },
        ...Array(5).fill(addNavItem).flat(),
        {
            content: "Save",
            trigger: ".modal-footer .btn:contains('Save')",
            run: "click",
        },
        {
            content: "Check that modal has disappeared",
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: `:iframe .o_homepage_editor_welcome_message:contains(welcome to your homepage)`,
        },
        ...clickOnEditAndWaitEditMode(),
        getTheLayoutChildren,
        {
            content: "Click on the navbar",
            trigger: ":iframe nav",
            run: "click",
        },
        {
            content: "Change content width",
            trigger: ".hb-row[data-label='Content Width'] .o-hb-btn[title='Small']",
            run: "click",
        },
        checkThatLayoutChanged,
        {
            content: "Make content width large",
            trigger: ".hb-row[data-label='Content Width'] .o-hb-btn[title='Full']",
            run: "click",
        },
        getTheLayoutChildren,
        {
            content: "Go to the Theme Tab",
            trigger: ".o-website-builder_sidebar .o-snippets-tabs [data-name='theme']",
            run: "click",
        },
        {
            content: "Change the page layout",
            trigger: ".hb-row[data-label='Page Layout'] .o-dropdown",
            run: "click",
        },
        {
            content: "Set the page layout to 'boxed'",
            trigger: ".o-hb-select-dropdown-item[data-action-value='boxed']",
            run: "click",
        },
        checkThatLayoutChanged,
    ]
);
