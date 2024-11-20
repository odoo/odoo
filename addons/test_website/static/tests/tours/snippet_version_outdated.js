import {
    registerWebsitePreviewTour,
    insertSnippet
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("snippet_version_outdated", {
    edition: true,
    url: "/",
}, () => [
    ...insertSnippet({
        id: 's_crashing_snippet',
        name: 'Test Crashing snip',
        groupName: "Content",
    }),
    {
        content: "Change s_crashing_snippet version",
        trigger: ':iframe #wrap.o_editable .s_crashing_snippet',
        run: function () {
            const iframe = document.querySelector('iframe');
            const snippet = iframe.contentDocument.querySelector('.s_crashing_snippet');
            snippet.setAttribute('data-vxml', "999");
        }
    },
    {
        content: "Edit s_crashing_snippet",
        trigger: ':iframe #wrap.o_editable .s_crashing_snippet',
        run: "click"
    },
    {
        trigger: ".snippet-option-CrashSnippet",
    },
    {
        content: "Edit s_crashing_snippet",
        trigger: '.snippet-option-CrashSnippet we-button.o_we_user_value_widget',
        run: "click"
    },
    {
        trigger: ".modal-dialog:contains(This snippet is outdated)",
    },
    {
        content: "The snippet is outdated, an alert message was send",
        trigger: 'body'
    }
]);