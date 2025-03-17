/** @odoo-module **/

import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

/**
 * The purpose of this tour is to check the custom snippets flow:
 *
 * -> go to edit mode
 * -> drag a banner into page content
 * -> customize banner (set text)
 * -> save banner as custom snippet
 * -> confirm save
 * -> ensure custom snippet is available in the "add snippet" dialog
 * -> add custom snippet into the page
 * -> ensure block appears as banner
 * -> ensure block appears as custom banner
 * -> rename custom banner
 * -> verify rename took effect
 * -> delete custom snippet
 * -> confirm delete
 * -> ensure it was deleted
 */

registerWebsitePreviewTour('test_custom_snippet', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_banner',
        name: 'Banner',
        groupName: "Intro",
    }),
    {
        content: "Customize snippet",
        trigger: ":iframe #wrapwrap .s_banner h1",
        run: "editor Test",
    },
    {
        content: "Save custom snippet",
        trigger: ".snippet-option-SnippetSave we-button",
        run: "click",
    },
    {
        content: "Confirm reload",
        trigger: ".modal-dialog button:contains('Save and Reload')",
        run: "click",
    },
    {
        content: "Click on the Custom category block",
        trigger: "#oe_snippets .oe_snippet[name='Custom'].o_we_draggable .oe_snippet_thumbnail",
        run: "click",
    },
    {
        content: "Ensure custom snippet preview appeared in the dialog",
        trigger: ":iframe .o_snippet_preview_wrap[data-snippet-id='s_banner'] section[data-name='Custom Banner']",
    },
    {
        content: "Rename custom snippet",
        trigger: ":iframe .o_custom_snippet_wrap > .o_custom_snippet_edit > button",
        run: "click",
    },
    {
        content: "Set name",
        trigger: ".o_rename_custom_snippet_dialog input[id='customSnippetName']",
        run: "edit Bruce Banner",
    },
    {
        content: "Confirm rename",
        trigger: ".o_rename_custom_snippet_dialog footer .btn-primary",
        run: "click",
    },
    {
        content: "Click on the 'Bruce Banner' snippet",
        trigger: ":iframe .o_snippet_preview_wrap[data-snippet-id='s_banner']:has(section[data-name='Bruce Banner'])",
        run: "click",
    },
    {
        content: "Ensure banner section exists",
        trigger: ":iframe #wrap section[data-name='Banner']",
    },
    {
        content: "Ensure custom banner section exists",
        trigger: ":iframe #wrap section[data-name='Bruce Banner']",
    },
    {
        content: "Click on the Custom category block",
        trigger: "#oe_snippets .oe_snippet[name='Custom'].o_we_draggable .oe_snippet_thumbnail",
        run: "click",
    },
    {
        content: "Delete custom snippet",
        trigger: ":iframe .o_custom_snippet_wrap > .o_custom_snippet_edit > button + button",
        run: "click",
    },
    {
        content: "Confirm delete",
        trigger: ".modal-dialog button:contains('Yes')",
        run: "click",
    },
    {
        content: "Ensure custom snippet disappeared",
        trigger: ":iframe .o_add_snippets_preview:not(:has(section[data-name='Bruce Banner']))",
    },
]);
