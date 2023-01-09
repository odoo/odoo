/** @odoo-module */

import wTourUtils from 'website.tour_utils';

const snippets = [
    {
        id: 's_text_image',
        name: 'Text - Image',
    },
];
wTourUtils.registerWebsitePreviewTour('conditional_visibility_1', {
    edition: true,
    url: '/',
    test: true,
}, [
wTourUtils.dragNDrop(snippets[0]),
wTourUtils.clickOnSnippet(snippets[0]),
wTourUtils.changeOption('ConditionalVisibility', 'we-toggler'),
{
    content: 'click on conditional visibility',
    trigger: '[data-name="visibility_conditional"]',
    run: 'click',
},
{
    content: 'click on utm medium toggler',
    trigger: '[data-save-attribute="visibilityValueUtmMedium"] we-toggler',
    run: 'click',
},
{
    trigger: '[data-save-attribute="visibilityValueUtmMedium"] we-selection-items [data-add-record="Email"]',
    content: 'click on Email',
    run: 'click',
},
...wTourUtils.clickOnSave(),
{
    content: 'Check if the rule was applied',
    extra_trigger: '.o_website_preview:only-child',
    trigger: 'iframe #wrap',
    run: function (actions) {
        const style = window.getComputedStyle(this.$anchor[0].getElementsByClassName('s_text_image')[0]);
        if (style.display !== 'none') {
            console.error('error This item should be invisible and only visible if utm_medium === email');
        }
    },
},
wTourUtils.clickOnEdit(),
{
    content: 'Check if the element is visible as it should always be visible in edit view',
    extra_trigger: 'body.editor_has_snippets',
    trigger: 'iframe #wrap .s_text_image',
    run: function (actions) {
        const style = window.getComputedStyle((this.$anchor[0]));
        if (style.display === 'none') {
            console.error('error This item should now be visible because utm_medium === email');
        }
    },
},
]);
