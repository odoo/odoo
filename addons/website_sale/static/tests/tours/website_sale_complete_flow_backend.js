/** @odoo-module **/

import { clickOnSave, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('website_sale_tour_backend', {
    url: '/shop/cart',
    edition: true,
}, () => [
        {
            content: "open customize tab",
            trigger: '.o_we_customize_snippet_btn',
            run: "click",
        },
        {
            trigger: "#oe_snippets .o_we_customize_panel",
        },
        {
            content: "Enable Extra step",
            trigger: '[data-customize-website-views="website_sale.extra_info"] we-checkbox',
            run: "click",
        },
        ...clickOnSave(),
    ],
);
