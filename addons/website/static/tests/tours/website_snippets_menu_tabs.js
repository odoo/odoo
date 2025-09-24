import { goToTheme, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_snippets_menu_tabs",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...goToTheme(),
        {
            trigger: "div[data-container-title='Colors'] div.we-bg-options-container",
        },
        {
            content: "Click on the empty 'DRAG BUILDING BLOCKS HERE' area.",
            trigger: ":iframe main > .oe_structure.oe_empty",
            run: "click",
        },
        ...goToTheme(),
        {
            content: "Verify that the customize panel is not empty.",
            trigger: ".o_theme_tab .options-container",
        },
        {
            content: "Click on the style tab.",
            trigger: "button[data-name='customize']",
            run: "click",
        },
        ...goToTheme(),
        {
            content: "Verify that the customize panel is not empty.",
            trigger: ".o_theme_tab .options-container",
        },
    ]
);
