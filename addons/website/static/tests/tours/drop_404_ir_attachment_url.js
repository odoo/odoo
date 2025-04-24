import {
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

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
        trigger: ".o-tab-content [data-container-title='Image'] [data-action-id='replaceMedia']",
    },
    {
        content: 'Once the image UI appears, check the image has no size (404)',
        trigger: ":iframe [data-snippet='s_404_snippet'] img",
        run() {
            const imgEl = this.anchor;
            if (!imgEl.complete
                || imgEl.naturalWidth !== 0
                || imgEl.naturalHeight !== 0) {
                throw new Error('This is supposed to be a 404 image');
            }
        },
    },
    {
        content: 'Click on the shape option',
        trigger: ".o-tab-content [data-container-title='Image'] .dropdown-toggle",
        run: "click",
    },
    {
        content: "Check the shape option page container is open",
        trigger: ".o_customize_tab [data-shape-group-id='basic']",
    },
    {
        content: 'Select the first shape',
        trigger: ".o_customize_tab .builder_select_page [data-action-value='html_builder/geometric/geo_shuriken']",
        run: "click",
    },
    {
        content: 'Once the shape is applied, check the image has now a size (placeholder image)',
        trigger: ":iframe [data-snippet='s_404_snippet'] img[src^='data:']",
        run() {
            return new Promise((resolve, reject) => {
                const imgEl = this.anchor;
                if (!imgEl.complete) {
                    return imgEl.naturalWidth === 0 || imgEl.naturalHeight === 0
                        ? reject(new Error("Even though the original image was a 404, the option should have been applied on the placeholder image"))
                        : resolve();
                }
            });
        },
    },
]);
