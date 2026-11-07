/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

const WEBSITE_MAIN_COLOR = '#ABCDEF';

wTourUtils.registerWebsitePreviewTour('website_text_edition', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.goToTheme(),
    {
        content: "Open colorpicker to change website main color",
        trigger: 'we-select[data-color="o-color-1"] .o_we_color_preview',
    },
    {
        content: "Input the value for the new website main color (also make sure it is independent from the backend)",
        trigger: '.o_hex_input',
        run: `text_blur ${WEBSITE_MAIN_COLOR}`,
    },
    wTourUtils.goBackToBlocks(),
    wTourUtils.dragNDrop({id: 's_text_block', name: 'Text'}),
    {
        content: "Click on the text block first paragraph (to auto select)",
        trigger: 'iframe .s_text_block p',
    },
    {
        content: "Open the foreground colorpicker",
        trigger: '#toolbar:not(.oe-floating) #oe-text-color',
    },
    {
        content: "Go to the 'solid' tab",
        trigger: '.o_we_colorpicker_switch_pane_btn[data-target="custom-colors"]',
    },
    {
        content: "Input the website main color explicitly",
        trigger: '.o_hex_input',
        run: `text_blur ${WEBSITE_MAIN_COLOR}`,
    },
    {
        content: "Check that paragraph now uses the main color *class*",
        trigger: 'iframe .s_text_block p',
        run: function (actions) {
            const fontEl = this.$anchor[0].querySelector('font');
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
