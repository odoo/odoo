import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("snippet_version_1", {
    edition: true,
    url: "/",
}, () => [
    ...insertSnippet({
        id: 's_test_snip',
        name: 'Test snip',
        groupName: "Content",
    }),
    ...insertSnippet({
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    }),
    {
    content: "Test t-snippet and t-snippet-call: snippets have data-snippet set",
    trigger: '.o-snippets-menu .o_snippets_container_body > .o_snippet',
    run: function () {
        // Tests done here as all these are not visible on the page
        const draggableSnippets = [...document.querySelectorAll('.o-snippets-menu .o_snippets_container_body > .o_snippet:not([data-module-id]) > :nth-child(2)')];
        if (draggableSnippets.length && !draggableSnippets.every(el => el.dataset.snippet)) {
            console.error("error Some t-snippet are missing their template name or there are no snippets to drop");
        }
        if (!document.querySelector('iframe:not(.o_ignore_in_tour)').contentDocument.querySelector('#wrap [data-snippet="s_test_snip"] [data-snippet="s_share"]')) {
            console.error("error Dropped a s_test_snip snippet but missing s_share template name in it");
        }
    },
},
    ...clickOnSave(),
]);
registerWebsitePreviewTour("snippet_version_2", {
    edition: true,
    url: "/",
}, () => [
{
    content: "Edit s_test_snip",
    trigger: ':iframe #wrap.o_savable .s_test_snip',
    run: "click",
},
{
    trigger:
        ".o_customize_tab .options-container[data-container-title='Test snip'] .o_we_version_control",
},
{
    content: "Edit text_image",
    trigger: ':iframe #wrap.o_savable .s_text_image',
    run: "click",
},
{
    trigger:
        ".o_customize_tab .options-container[data-container-title='Text - Image'] .o_we_version_control",
},
{
    content: "Edit s_share",
    trigger: ':iframe #wrap.o_savable .s_share',
    run: "click",
},
{
    trigger:
        ".o_customize_tab .options-container[data-container-title='Block'] .o_we_version_control",
},
{
    content: "s_share is outdated",
    trigger: ':iframe body',
}]);
