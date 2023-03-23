/** @odoo-module */

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour("website_media_dialog_undraw", {
    test: true,
    url: '/',
    edition: true,
}, [
wTourUtils.dragNDrop({
    id: 's_text_image',
    name: 'Text - Image',
}),
{
    trigger: '.s_text_image img',
    run: "dblclick",
},
{
    trigger: '.o_select_media_dialog:has(.o_we_search_select option[value="media-library"])',
},
]);

wTourUtils.registerWebsitePreviewTour('website_media_dialog_icons', {
    test: true,
    url: '/',
    edition: true,
}, [
    wTourUtils.dragNDrop({
        id: 's_process_steps',
        name: 'Steps',
    }),
    {
        content: "Open MediaDialog from a snippet icon",
        trigger: 'iframe .s_process_steps .fa-unlock-alt',
        run: "dblclick",
    },
    {
        content: "Pick the same icon",
        trigger: '.o_select_media_dialog .o_we_attachment_selected.fa-unlock-alt',
    },
    {
        content: "Check if the icon remains the same",
        trigger: 'iframe .s_process_steps .fa-unlock-alt',
        run: () => null, // it's a check
    },
    {
        content: "Open MediaDialog again",
        trigger: 'iframe .s_process_steps .fa-unlock-alt',
        run: "dblclick",
    },
    {
        content: "Click on the ADD button",
        trigger: '.o_select_media_dialog .btn:contains(Add)',
    },
    {
        content: "Check if the icon remains the same",
        trigger: 'iframe .s_process_steps .fa-unlock-alt',
        run: () => null, // it's a check
    },
    ...wTourUtils.clickOnSave()
]);
