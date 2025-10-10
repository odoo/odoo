/** @odoo-module **/

import {
    changeOption,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import wUtils from '@website/js/utils';

registerWebsitePreviewTour('drop_404_ir_attachment_url', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_404_snippet',
        name: '404 Snippet',
        groupName: "Images",
    }),
    {
        content: 'Click on the snippet image',
        trigger: ':iframe .s_404_snippet img',
        run: "click",
    },
    {
        trigger: ".snippet-option-ReplaceMedia",
    },
    {
        content: 'Once the image UI appears, check the image has no size (404)',
        trigger: ':iframe .s_404_snippet img',
        async run() {
            const imgEl = this.anchor;
            await wUtils.onceAllImagesLoaded($(imgEl));
            if (imgEl.naturalWidth !== 0 || imgEl.naturalHeight !== 0) {
                throw new Error('This is supposed to be a 404 image');
            }
        },
    },
    changeOption('ImageTools', 'we-select[data-name="shape_img_opt"] we-toggler'),
    changeOption('ImageTools', 'we-button[data-set-img-shape]'),
    {
        content: 'Once the shape is applied, check the image has now a size (placeholder image)',
        trigger: ':iframe .s_404_snippet img[src^="data:"]',
        async run() {
            const imgEl = this.anchor;
            await wUtils.onceAllImagesLoaded($(imgEl));
            if (imgEl.naturalWidth === 0 || imgEl.naturalHeight === 0) {
                throw new Error('Even though the original image was a 404, the option should have been applied on the placeholder image');
            }
        },
    },
]);
