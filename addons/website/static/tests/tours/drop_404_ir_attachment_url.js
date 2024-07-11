/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('drop_404_ir_attachment_url', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: 's_404_snippet',
        name: '404 Snippet',
    }),
    {
        content: 'Click on the snippet image',
        trigger: 'iframe .s_404_snippet img',
    }, {
        content: 'Once the image UI appears, check the image has no size (404)',
        trigger: 'iframe .s_404_snippet img',
        extra_trigger: '.snippet-option-ReplaceMedia',
        run: function () {
            const imgEl = this.$anchor[0];
            if (!imgEl.complete
                    || imgEl.naturalWidth !== 0
                    || imgEl.naturalHeight !== 0) {
                console.error('This is supposed to be a 404 image');
            }
        },
    },
    wTourUtils.changeOption('ImageTools', 'we-select[data-name="shape_img_opt"] we-toggler'),
    wTourUtils.changeOption('ImageTools', 'we-button[data-set-img-shape]'),
    {
        content: 'Once the shape is applied, check the image has now a size (placeholder image)',
        trigger: 'iframe .s_404_snippet img[src^="data:"]',
        run: function () {
            const imgEl = this.$anchor[0];
            if (!imgEl.complete
                    || imgEl.naturalWidth === 0
                    || imgEl.naturalHeight === 0) {
                console.error('Even though the original image was a 404, the option should have been applied on the placeholder image');
            }
        },
    },
]);
