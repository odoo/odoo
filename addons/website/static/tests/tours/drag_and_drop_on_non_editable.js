/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour("test_drag_and_drop_on_non_editable", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: "s_company_team",
        name: "Team",
    }),
    {
        content: "Click on an editable media in non editable env.",
        trigger: "iframe .s_company_team .o_not_editable > .o_editable_media",
    },
    {
        content: "Verify that the Replace options is in the editor.",
        trigger: "we-button[data-replace-media]",
        isCheck: true,
    },
    wTourUtils.goBackToBlocks(),
    Object.assign(wTourUtils.dragNDrop({
        id: "s_text_highlight",
        name: "Text Highlight",
    }), {
        content: "Drag and drop the Text Highlight building block next to the Team block media.",
        run: "drag_and_drop_native iframe .s_company_team .o_not_editable > .o_editable_media",
    }),
    {
        content: "Verify that the Text Highlight building block isn't in a non editable element.",
        trigger: "iframe .s_company_team :not(.o_not_editable) > .s_text_highlight",
        isCheck: true,
    },
]);
