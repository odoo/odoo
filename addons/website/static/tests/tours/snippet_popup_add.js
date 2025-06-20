import {
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('snippet_popup_add', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        name: "Popup",
        id: "s_popup",
        groupName: "Content",
    }),
    {
        content: "Click on the Popup snippet to edit it.",
        trigger: ":iframe #wrap.o_editable [data-snippet='s_popup']:not(:visible)",
        run: "click",
    },
]);
