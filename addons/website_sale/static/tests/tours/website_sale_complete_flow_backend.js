import { clickOnSave, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('website_sale_tour_backend', {
    url: '/shop/cart',
    edition: true,
}, () => [
        {
            content: "open customize tab",
            trigger: "[data-name='customize']",
            run: "click",
        },
        {
            trigger: ".o_builder_sidebar_open .o_customize_tab",
        },
        {
            content: "Enable Extra step",
            trigger: "[data-action-param='{\"views\":[\"website_sale.extra_info\"]}'] input[type='checkbox']",
            run: "click",
        },
        ...clickOnSave(),
    ],
);
