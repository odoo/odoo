/** @odoo-module **/

import tour from 'web_tour.tour';

const subcontractingPortalSteps = [{
    trigger: 'table > tbody > tr a:has(span:contains(WH/IN/00))',
    content: 'Select the picking to open the backend view.',
    run: 'click',
},{
    trigger: '.o_subcontracting_portal',
    content: 'Wait the subcontracting portal to be loaded.',
    run: function () {},
}, {
    trigger: 'button[name="action_show_details"]',
    run: 'click',
}];

tour.register('subcontracting_portal_tour', {
    test: true,
    url: '/my/productions',
}, subcontractingPortalSteps);
