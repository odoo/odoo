/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour("editable_root_as_custom_snippet", {
    test: true,
    edition: true,
    url: '/custom-page',
}, () => [
    wTourUtils.clickOnSnippet('.s_title.custom[data-oe-model][data-oe-id][data-oe-field][data-oe-xpath]'),
    wTourUtils.changeOption('SnippetSave', 'we-button'),
    {
        content: "Confirm modal",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Wait for the custom snippet to appear in the panel",
        trigger: '.oe_snippet[name="Custom Title"]',
        isCheck: true,
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Go to homepage",
        trigger: 'iframe a[href="/"].nav-link',
    },
    {
        content: "Wait to land on homepage",
        trigger: 'iframe a[href="/"].nav-link.active',
        isCheck: true,
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.dragNDrop({id: 's_title', name: 'Custom Title'}),
    {
        content: "Check that the custom snippet does not have branding",
        trigger: 'iframe #wrap .s_title.custom:not([data-oe-model]):not([data-oe-id]):not([data-oe-field]):not([data-oe-xpath])',
        isCheck: true,
    },
]);
