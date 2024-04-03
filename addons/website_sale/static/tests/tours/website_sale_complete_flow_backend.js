/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('website_sale_tour_backend', {
    test: true,
    url: '/shop/cart',
    edition: true,
}, [
        {
            content: "open customize tab",
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
