/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour("website_snippets_menu_tabs", {
    test: true,
    url: "/",
    edition: true,
}, [
    wTourUtils.goToTheme(),
    {
        content: "Click on the empty 'DRAG BUILDING BLOCKS HERE' area.",
        extra_trigger: 'we-customizeblock-option.snippet-option-ThemeColors',
        trigger: 'iframe main > .oe_structure.oe_empty',
        run: 'click',
    },
    wTourUtils.goToTheme(),
    {
        content: "Verify that the customize panel is not empty.",
        trigger: '.o_we_customize_panel > we-customizeblock-options',
        run: () => null, // it's a check
    },
    {
        content: "Click on the style tab.",
        trigger: '#snippets_menu .o_we_customize_snippet_btn',
    },
    wTourUtils.goToTheme(),
    {
        content: "Verify that the customize panel is not empty.",
        trigger: '.o_we_customize_panel > we-customizeblock-options',
        run: () => null, // it's a check
    },
]);
