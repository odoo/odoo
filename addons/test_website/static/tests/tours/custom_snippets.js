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
        trigger: "div[data-container-title='Banner'] .oe_snippet_save",
        run: "click",
    },
    {
        content: "Confirm reload",
        trigger: ".modal-dialog button:contains('Save')",
        run: "click",
    },
    {
        content: "Click on the block tab",
        trigger: ".o-snippets-tabs button[data-name='blocks']",
        run: "click",
    },
    {
        content: "Click on the Custom category block",
        trigger: ".o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name='Custom'].o_draggable .o_snippet_thumbnail .o_snippet_thumbnail_area",
        run: "click",
    },
    {
        content: "Ensure custom snippet preview appeared in the dialog",
        trigger: ":iframe .o_snippet_preview_wrap[data-snippet-id^='s_banner_'] section[data-name='Custom Banner']",
    },
    {
        content: "Rename custom snippet",
        trigger: ":iframe .o_custom_snippet_edit > button",
        run: "click",
    },
    {
        content: "Set name",
        trigger: ".modal-dialog:not(.o_inactive_modal body) input[id='inputConfirmation']",
        run: "edit Bruce Banner",
    },
    {
        content: "Confirm rename",
        trigger: ".modal-dialog:not(.o_inactive_modal body) footer .btn-primary",
        run: "click",
    },
    {
        content: "Click on the 'Bruce Banner' snippet",
        trigger: ":iframe .o_snippet_preview_wrap[data-snippet-id^='s_banner_']:has(section[data-name='Bruce Banner'])",
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
        trigger: ".o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name='Custom'].o_draggable .o_snippet_thumbnail .o_snippet_thumbnail_area",
        run: "click",
    },
    {
        content: "Delete custom snippet",
        trigger: ":iframe .o_custom_snippet_edit > button + button",
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
