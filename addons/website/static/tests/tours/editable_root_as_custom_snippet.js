/** @odoo-module **/

import tour from 'web_tour.tour';
import wTourUtils from 'website.tour_utils';

tour.register("editable_root_as_custom_snippet", {
    test: true,
}, [
    wTourUtils.clickOnSnippet('.s_title.custom[data-oe-model][data-oe-id][data-oe-field][data-oe-xpath]'),
    wTourUtils.changeOption('SnippetSave', 'we-button'),
    {
        content: "Confirm modal",
        trigger: '.modal-footer .btn-primary',
    },
    {
        content: "Wait for the custom snippet to appear in the panel",
        trigger: '.oe_snippet[name="Custom Title"]',
        run: () => null,
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Go to homepage",
        trigger: 'iframe a[href="/"].nav-link',
    },
    {
        content: "Wait to land on homepage",
        trigger: 'iframe a[href="/"].nav-link.active',
        run: () => null,
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    wTourUtils.dragNDrop({id: 's_title', name: 'Custom Title'}),
    {
        content: "Check that the custom snippet does not have branding",
        trigger: 'iframe #wrap .s_title.custom:not([data-oe-model]):not([data-oe-id]):not([data-oe-field]):not([data-oe-xpath])',
        run: () => null,
    },
]);
