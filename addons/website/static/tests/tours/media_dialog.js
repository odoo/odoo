/** @odoo-module */

import {
    changeOption,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("website_media_dialog_undraw", {
    url: '/',
    edition: true,
}, () => [
...insertSnippet({
    id: 's_text_image',
    name: 'Text - Image',
    groupName: "Content",
}),
{
    content: "Open the media dialog from the snippet",
    trigger: ":iframe .s_text_image img",
    run: "dblclick",
}, {
    content: "Search for 'banner' to call the media library", // Mocked call
    trigger: ".o_select_media_dialog .o_we_search",
    run: "edit banner",
}, {
    content: "Check that the media library is available",
    trigger: '.o_select_media_dialog:has(.o_we_search_select option[value="media-library"])',
},
]);

registerWebsitePreviewTour("website_media_dialog_external_library", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: "s_text_image",
        name: "Text - Image",
        groupName: "Content",
    }),
    {
        content: "Open the media dialog from the snippet",
        trigger: ":iframe .s_text_image img",
        run: "dblclick",
    }, {
        content: "Dummy search to call the media library",
        trigger: ".o_select_media_dialog .o_we_search",
        run: "edit a",
    }, {
        content: "Choose the media library to only show its media",
        trigger: ".o_select_media_dialog .o_we_search_select",
        run: "select Illustrations",
    }, {
        content: "Double click on the first image",
        trigger: ".o_select_media_dialog img.o_we_attachment_highlight",
        run: "click",
    }, {
        content: "Reopen the media dialog",
        trigger: ":iframe .s_text_image img",
        run: "dblclick",
    }, {
        content: "Check that the image was created only once",
        trigger: ".o_select_media_dialog .o_we_existing_attachments .o_existing_attachment_cell img[src^='/html_editor/shape/illustration/']",
        run() {
            const listEl = this.anchor.closest(".o_select_media_dialog .o_we_existing_attachments");
            const selector = ".o_existing_attachment_cell img[src^='/html_editor/shape/illustration/']";
            const uploadedImgs = listEl.querySelectorAll(`${selector}[title='${this.anchor.title}']`);
            if (uploadedImgs.length !== 1) {
                throw new Error(`${uploadedImgs.length} attachment(s) were found. Exactly 1 should have been created.`);
            }
        },
    },
]);

registerWebsitePreviewTour('website_media_dialog_icons', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_social_media',
        name: 'Social Media',
    }),
    {
        content: "Open MediaDialog from a snippet icon",
        trigger: ':iframe .s_social_media .fa-instagram',
        run: "dblclick",
    },
    {
        content: "Pick the same icon",
        trigger: '.o_select_media_dialog .o_we_attachment_selected.fa-instagram',
        run: "click",
    },
    {
        content: "Check if the icon remains the same",
        trigger: ':iframe .s_social_media .fa-instagram',
    },
    {
        content: "Open MediaDialog again",
        trigger: ':iframe .s_social_media .fa-instagram',
        run: "dblclick",
    },
    {
        content: "Click on the ADD button",
        trigger: '.o_select_media_dialog .btn:contains(Add)',
        run: "click",
    },
    {
        content: "Check if the icon remains the same",
        trigger: ':iframe .s_social_media .fa-instagram',
    },
    ...clickOnSave()
]);

registerWebsitePreviewTour("website_media_dialog_image_shape", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: "s_text_image",
        name: "Text - Image",
        groupName: "Content",
    }),
    {
        content: "Click on the image",
        trigger: ":iframe .s_text_image img",
        run: "click",
    },
    changeOption("ImageTools", 'we-select[data-name="shape_img_opt"] we-toggler'),
    changeOption("ImageTools", "we-button[data-set-img-shape]"),
    {
        content: "Open MediaDialog from an image",
        trigger: ":iframe .s_text_image img[data-shape]",
        run: "dblclick",
    },
    {
        content: "Click on the 'Icons' tab",
        trigger: '.o_select_media_dialog .o_notebook_headers .nav-item a:contains("Icons")',
        run: "click",
    },
    {
        content: "Select an icon",
        trigger: ".o_select_media_dialog:has(.nav-link.active:contains('Icons')) .tab-content span.fa-heart",
        run: "click",
    },
    {
        content: "Checks that the icon doesn't have a shape",
        trigger: ":iframe .s_text_image .fa-heart:not([data-shape])",
    },
]);
