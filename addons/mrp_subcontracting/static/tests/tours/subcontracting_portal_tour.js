import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('subcontracting_portal_tour', {
    url: '/my/productions',
    steps: () => [
        {
            trigger: 'table > tbody > tr a:has(span:contains(WH/IN/00))',
            content: 'Select the picking to open the backend view.',
            run: 'click',
            expectUnloadPage: true,
        },{
            trigger: ':iframe .o_subcontracting_portal',
            content: 'Wait the subcontracting portal to be loaded.',
        }, {
            trigger: ':iframe button[name="action_show_subcontract_details"]',
            run: 'click',
        }
    ],
});
