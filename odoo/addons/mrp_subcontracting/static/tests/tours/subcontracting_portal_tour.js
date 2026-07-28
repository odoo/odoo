/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('subcontracting_portal_tour', {
    test: true,
    url: '/my/productions',
    steps: () => [
        {
            trigger: 'table > tbody > tr a:has(span:contains(WH/IN/00))',
            content: 'Select the picking to open the backend view.',
            run: 'click',
        },{
            trigger: 'iframe .o_subcontracting_portal',
            content: 'Wait the subcontracting portal to be loaded.',
            run: function () {},
        }, {
            trigger: 'iframe button[name="action_show_details"]',
            run: 'click',
        }
    ],
});
