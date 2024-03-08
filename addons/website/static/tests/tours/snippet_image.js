/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("snippet_image", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({id: "s_image", name: "Image"}),
{
    content: "Verify if the media dialog opens",
    trigger: ".o_select_media_dialog",
    isCheck: true,
},
{
    content: "Close the media dialog",
    trigger: ".o_select_media_dialog .btn-close",
},
{
    content: "Verify if the image placeholder has been removed",
    trigger: ":iframe footer:not(:has(.s_image > svg))",
    isCheck: true,
},
    wTourUtils.dragNDrop({id: "s_image", name: "Image"}),
{
    content: "Verify that the image placeholder is within the page",
    trigger: ":iframe footer .s_image > svg",
    in_modal: false,
    isCheck: true,
},
{
    content: "Click on the image",
    trigger: ".o_select_media_dialog .o_we_media_dialog_img_wrapper img",
},
{
    content: "Verify if the image has been added in the footer and if the image placeholder has been removed",
    trigger: ":iframe footer:not(:has(.s_image > svg)) img.o_we_custom_image",
    isCheck: true,
},
{
    content: "Click on the 'undo' button",
    trigger: '#oe_snippets button.fa-undo',
},
{
    content: "Check that the image and the image placeholder have been removed",
    trigger: ":iframe footer:not(:has(.s_image > svg)):not(:has(img.o_we_custom_image))",
    isCheck: true,
},
]);
