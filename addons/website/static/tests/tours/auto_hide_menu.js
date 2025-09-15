import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

let numNavChildren;

const getTheLayoutChildren = {
    content: "Get the number of elements in the navbar",
    trigger: ":iframe #o_main_nav ul[role='menu']",
    async run({ animationFrame }) {
        await animationFrame();
        numNavChildren = this.anchor.children.length;
    },
};

const checkThatLayoutChanged = {
    content: "Ensure that the navbar layout has changed",
    trigger: ":iframe #o_main_nav ul[role='menu']",
    async run({ animationFrame }) {
        await animationFrame();
        if (this.anchor.children.length === numNavChildren) {
            throw new Error("Navbar layout should change");
        }
    },
};

registerWebsitePreviewTour(
    "website_auto_hide_menu",
    {
        edition: true,
        url: "/",
    },
    () => [
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
