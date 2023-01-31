/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('shop_editor', {
    test: true,
    url: '/shop?enable_editor=1',
}, [{
    content: "Click on pricelist dropdown",
    trigger: "div.o_pricelist_dropdown a[data-toggle=dropdown]",
}, {
    trigger: "input[name=search]",
    extra_trigger: "div.o_pricelist_dropdown a[data-toggle=dropdown][aria-expanded=true]",
    content: "Click somewhere else in the shop.",
}, {
    trigger: "div.o_pricelist_dropdown a[data-toggle=dropdown]",
    extra_trigger: "div.o_pricelist_dropdown a[data-toggle=dropdown][aria-expanded=false]",
    content: "Click on the pricelist again.",
}]);
