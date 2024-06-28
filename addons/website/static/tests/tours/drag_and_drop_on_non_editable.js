/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour("test_drag_and_drop_on_non_editable", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    ...wTourUtils.dragNDrop({
        id: "s_company_team",
        name: "Team",
    }),
    {
        content: "Click on an editable media in non editable env.",
        trigger: ":iframe .s_company_team .o_not_editable > .o_editable_media",
        run: "click",
    },
    {
        content: "Verify that the Replace options is in the editor.",
        trigger: "we-button[data-replace-media]",
    },
    wTourUtils.goBackToBlocks(),
    {
        trigger: ".o_website_preview.editor_enable.editor_has_snippets",
    },
    {
        content: "Drag and drop the Text Highlight building block next to the Team block media.",
        trigger: `#oe_snippets .oe_snippet[name="Text Highlight"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_already_dragging)`,
        run: "drag_and_drop :iframe .s_company_team .o_not_editable > .o_editable_media",
    },
    {
        content: "Verify that the Text Highlight building block isn't in a non editable element.",
        trigger: ":iframe .s_company_team :not(.o_not_editable) > .s_text_highlight",
    },
]);
