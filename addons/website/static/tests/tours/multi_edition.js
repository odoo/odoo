/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('website_multi_edition', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    {
        content: 'Check the current page has not the elements that will be added',
        trigger: ':iframe body:not(:has(.s_text_image)):not(:has(.s_hr))',
        run: () => null,
    },
    // Edit the main element of the page
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    // Edit another part in the page, like the footer
    // TODO: use wTourUtils.dragNDrop() instead
    {
        trigger: `#oe_snippets .oe_snippet[name="Separator"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_already_dragging)`,
        extra_trigger: ".o_website_preview.editor_enable.editor_has_snippets",
        content: "Drag the Separator building block and drop it at the bottom of the page.",
        run: "drag_and_drop :iframe .oe_drop_zone:last",
    },
    ...wTourUtils.clickOnSave(),
    {
        content: 'Check that the main element of the page was properly saved',
        trigger: ':iframe main .s_text_image',
        run: () => null,
    },
    {
        content: 'Check that the footer was properly saved',
        trigger: ':iframe footer .s_hr',
        run: () => null,
    },
]);
