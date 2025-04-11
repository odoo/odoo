import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
    testSwitchWebsite,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('snippet_cache_across_websites', {
    edition: true,
    url: '/@/'
}, () => [
    {
        content: "Click on the Custom category block",
        trigger: ".o-snippets-menu .o_snippet[name='Custom'].o_draggable .o_snippet_thumbnail_area",
        run: "click",
    },
    {
        content: "Ensure custom snippet preview appeared in the dialog",
        trigger: ":iframe .o_snippet_preview_wrap section.s_custom_snippet",
    },
    {
        content: "Close the 'add snippet' dialog",
        trigger: ".o_add_snippet_dialog .modal-header .btn-close",
        run: "click",
    },
    // There's no need to save, but canceling might or might not show a popup...
    ...clickOnSave(),
    ...testSwitchWebsite('Test Website'),
    ...clickOnEditAndWaitEditMode(),
    {
        content: "Check that the custom snippet category is not here",
        trigger: ".o-snippets-menu:not(:has(.o_snippet[name='Custom']))",
    },
]);
