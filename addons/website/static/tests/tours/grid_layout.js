/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

const snippet = {
    id: 's_text_image',
    name: 'Text - Image',
};

wTourUtils.registerWebsitePreviewTour('website_replace_grid_image', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.dragNDrop(snippet),
    wTourUtils.clickOnSnippet(snippet),
    {
        content: "Toggle to grid mode",
        trigger: '.o_we_user_value_widget[data-name="grid_mode"]',
    },
    {
        content: "Replace image",
        trigger: 'iframe .s_text_image img',
        run: 'dblclick',
    },
    {
        content: "Pick new image",
        trigger: '.o_select_media_dialog img[title="s_banner_default_image.jpg"]',
    },
    {
        content: "Add new image column",
        trigger: '.o_we_user_value_widget[data-add-element="image"]',
    },
    {
        content: "Replace new image",
        trigger: 'iframe .s_text_image img[src="/web/image/website.s_text_image_default_image"]',
        run: 'dblclick',
    },
    {
        content: "Pick new image",
        trigger: '.o_select_media_dialog img[title="s_banner_default_image.jpg"]',
    },
    ...wTourUtils.clickOnSave()
]);
