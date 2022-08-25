/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

wTourUtils.registerEditionTour('website_sale_tour_backend', {
    test: true,
    url: '/shop/cart',
    edition: true,
}, [
        {
            content: "open customize tab",
            extra_trigger: '#oe_snippets.o_loaded',
            trigger: '.o_we_customize_snippet_btn',
        },
        {
            content: "Enable Extra step",
            extra_trigger: '#oe_snippets .o_we_customize_panel',
            trigger: '[data-customize-website-views="website_sale.extra_info_option"] we-checkbox',
        },
        ...wTourUtils.clickOnSave(),
    ],
);
