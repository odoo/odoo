/** @odoo-module */

import tour from 'web_tour.tour';

const checkNonEditable = {
    trigger: 'section.s_company_team div.o_not_editable[contenteditable="false"]',
    content: 'Check non editable parts.',
    run: () => {},
};

tour.register('non_editable_content', {
    test: true,
    url: '?enable_editor=1',
}, [{
    trigger: '#snippet_feature .oe_snippet:has(span:contains("Team")) .oe_snippet_thumbnail',
    content: 'Drag the Team block and drop it in your page.',
    run: 'drag_and_drop #wrap',
},
checkNonEditable,
{
    trigger: '[data-action=save]:contains("Save")',
    content: 'Click the Save button.',
    extra_trigger: '.homepage',
},
{
    trigger: '[data-action=edit]:contains("Edit")',
    content: 'Click the Edit button.',
    extra_trigger: '.homepage',
},
checkNonEditable,
]);
