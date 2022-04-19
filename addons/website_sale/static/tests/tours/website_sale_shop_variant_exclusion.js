/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('shop_variant_exclusion', {
        url: '/shop',
        test: true,
    },
    [
        {
            content: "select product attribute First Attribute - Value 1",
            trigger: 'form.js_attributes input:not(:checked) + label:contains(First Attribute - Value 1)',
        },
        {
            content: "select product attribute Second Attribute - Value 2",
            trigger: 'form.js_attributes input:not(:checked) + label:contains(Second Attribute - Value 2)',
        },
        {
            content: "check for product template",
            trigger: '[data-oe-expression="product.name"]:contains(Test Product)',
            run: () => {}
        },
        {
            content: "deselect product attribute Second Attribute - Value 2",
            trigger: 'form.js_attributes input:checked + label:contains(Second Attribute - Value 2)',
        },
        {
            content: "select product attribute Second Attribute - Value 1",
            extra_trigger: 'body:not(:has(#customize-menu:visible .dropdown-menu:visible))',
            trigger: 'form.js_attributes input:not(:checked) + label:contains(Second Attribute - Value 1)',
        },
        {
            content: "check for no product defined",
            trigger: "h3:contains(No product defined)",
            run: () => {}
        },
    ]
);

