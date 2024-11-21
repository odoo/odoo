/** @odoo-module **/

import {
    insertSnippet,
    goBackToBlocks,
    goToTheme,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

const WEBSITE_MAIN_COLOR = '#ABCDEF';

registerWebsitePreviewTour('website_text_edition', {
    url: '/',
    edition: true,
}, () => [
    ...goToTheme(),
    {
        content: "Open colorpicker to change website main color",
        trigger: 'we-select[data-color="o-color-1"] .o_we_color_preview',
        run: "click",
    },
    {
        content: "Input the value for the new website main color (also make sure it is independent from the backend)",
        trigger: '.o_hex_input',
        run: `edit ${WEBSITE_MAIN_COLOR} && click body`,
    },
    goBackToBlocks(),
    ...insertSnippet({id: "s_text_block", name: "Text", groupName: "Text"}),
    {
        content: "Click on the text block first paragraph (to auto select)",
        trigger: ':iframe .s_text_block p',
        run: "click",
    },
    {
        content: "Open the foreground colorpicker",
        trigger: '#toolbar:not(.oe-floating) #oe-text-color',
        run: "click",
    },
    {
        content: "Go to the 'solid' tab",
        trigger: '.o_we_colorpicker_switch_pane_btn[data-target="custom-colors"]',
        run: "click",
    },
    {
        content: "Input the website main color explicitly",
        trigger: '.o_hex_input',
        run: `edit ${WEBSITE_MAIN_COLOR} && click body`,
    },
    {
        content: "Check that paragraph now uses the main color *class*",
        trigger: ':iframe .s_text_block p',
        run: function (actions) {
            const fontEl = this.anchor.querySelector("font");
            if (!fontEl) {
                console.error("A background color should have been applied");
                return;
            }
            if (fontEl.style.backgroundColor) {
                console.error("The paragraph should not have an inline style background color");
                return;
            }
            if (!fontEl.classList.contains('text-o-color-1')) {
                console.error("The paragraph should have the right background color class");
                return;
            }
        },
    }
]);
