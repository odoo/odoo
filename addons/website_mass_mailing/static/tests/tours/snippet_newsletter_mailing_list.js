import {
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('snippet_newsletter_mailing_list', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_newsletter_subscribe_form',
        name: 'Newsletter',
    }),
    {
        content: 'Select Newsletter to Edit',
        trigger: ':iframe div[data-name="Newsletter"]',
        run: 'click'
    },
    {
        content: 'Select Mailing List from Dropdown',
        trigger: 'div[data-label="Newsletter"] button.o-dropdown',
        run: 'click'
    },
    {
        content: 'Our Mailing List Should be visible there',
        trigger: 'div[role="menuitem"]:contains("Ben 10")',
    },
]);
