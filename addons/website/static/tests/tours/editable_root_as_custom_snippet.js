/** @odoo-module **/

import {
    changeOption,
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("editable_root_as_custom_snippet", {
    edition: true,
    url: '/custom-page',
    checkDelay: 400,
}, () => [
    ...clickOnSnippet('.s_title.custom[data-oe-model][data-oe-id][data-oe-field][data-oe-xpath]'),
    changeOption('SnippetSave', 'we-button'),
    {
        content: "Confirm modal",
        trigger: '.modal-footer .btn-primary',
        run: "click",
    },
    {
        content: "Wait for the custom category to appear in the panel",
        trigger: '.oe_snippet[name="Custom"]',
    },
    ...clickOnSave(),
    {
        content: "Go to homepage",
        trigger: ':iframe a[href="/"].nav-link',
        run: "click",
    },
    {
        content: "Wait to land on homepage",
        trigger: ':iframe a[href="/"].nav-link.active',
    },
    ...clickOnEditAndWaitEditMode(),
    ...insertSnippet({id: "s_title", name: "Custom Title", groupName: "Custom"}),
    {
        content: "Check that the custom snippet does not have branding",
        trigger: ':iframe #wrap .s_title.custom:not([data-oe-model]):not([data-oe-id]):not([data-oe-field]):not([data-oe-xpath])',
    },
]);
