/** @odoo-module **/
import { goBackToBlocks, goToTheme, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

function waitForCSSReload() {
    // TODO we should find a better way to wait for this in tests after CSS
    // reload, it is currently done multiple different ways depending on the
    // test.
    return [
        // This step is here because the option is applied but triggers a
        // reloading of the CC value, so if the second value is sent too soon,
        // it will be ignored. Clicking on the snippet tab and back will ensure
        // that the mutex is cleared, and therefore we can apply the saturation
        // step.
        goBackToBlocks(),
        ...goToTheme(),
        {
            content: "Wait for no loading",
            trigger: 'body:not(:has(.o_we_ui_loading)) :iframe body:not(:has(.o_we_ui_loading))',
        },
    ];
}

registerWebsitePreviewTour('website_gray_color_palette', {
    url: '/',
    edition: true,
}, () => [
    ...goToTheme(),
    {
        content: "Toggle gray color palette",
        trigger: '.o_we_gray_preview.o_we_collapse_toggler',
        run: "click",
    },
    {
        content: "Drag the hue slider",
        trigger: '.o_we_slider_tint[data-param="gray-hue"] input',
        run: "range 100",
    },
    {
        content: "Wait for loading",
        trigger: ":iframe body:has(.o_we_ui_loading)",
    },
    {
        content: "Check the preview of the gray 900 after hue change",
        trigger: '[variable="900"][style="background-color: rgb(36, 41, 33) !important;"]',
    },
    ...waitForCSSReload(),
    {
        content: "Drag the saturation slider",
        trigger: '.o_we_user_value_widget[data-param="gray-extra-saturation"] input',
        run: "range 15",
    },
    {
        content: "Wait for loading",
        trigger: ":iframe body:has(.o_we_ui_loading)",
    },
    {
        content: "Check the preview of the gray 900 after saturation change",
        trigger: '[variable="900"][style="background-color: rgb(34, 47, 27) !important;"]',
    },
    ...waitForCSSReload(),
    {
        content: "Wait for the iframe to be loaded",
        trigger: ':iframe body',
        run() {
            const iframeEl = document.querySelector('.o_website_preview .o_iframe');
            const styles = iframeEl.contentWindow.getComputedStyle(iframeEl.contentDocument.documentElement);
            if (styles.getPropertyValue('--900').toString().replace(/ /g, '') !== '#222F1B') {
                throw new Error('The value for the gray 900 is not right');
            }
        }
    },
]);
