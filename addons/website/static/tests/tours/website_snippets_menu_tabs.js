/** @odoo-module **/

import {
    goToTheme,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("website_snippets_menu_tabs", {
    url: "/",
    edition: true,
}, () => [
    ...goToTheme(),
    {
        trigger: "we-customizeblock-option.snippet-option-ThemeColors",
    },
    {
        content: "Click on the empty 'DRAG BUILDING BLOCKS HERE' area.",
        trigger: ':iframe main > .oe_structure.oe_empty',
        run: 'click',
    },
    ...goToTheme(),
    {
        content: "Verify that the customize panel is not empty.",
        trigger: '.o_we_customize_panel > we-customizeblock-options',
    },
    {
        content: "Click on the style tab.",
        trigger: '#snippets_menu .o_we_customize_snippet_btn',
        run: "click",
    },
    ...goToTheme(),
    {
        content: "Verify that the customize panel is not empty.",
        trigger: '.o_we_customize_panel > we-customizeblock-options',
    },
]);
