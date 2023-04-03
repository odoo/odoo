/** @odoo-module **/

import { registry } from "@web/core/registry";

var imageSelector = '#o-carousel-product .carousel-item.active img';
var imageName = "A Colorful Image";
var nameGreen = "Forest Green";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('shop_zoom', {
    test: true,
    url: '/shop?debug=1&search=' + imageName,
    steps: [
    {
        content: "select " + imageName,
        trigger: '.oe_product_cart a:containsExact("' + imageName + '")',
    },
    {
        content: "click on the image",
        trigger: imageSelector,
        run: 'clicknoleave',
    },
    {
        content: "check that the image viewer opened",
        trigger: '.o_wsale_image_viewer',
        run: () => {},
    },
    {
        content: "close the image viewer",
        trigger: '.o_wsale_image_viewer_header span.fa-times',
    },
    {
        content: "change variant",
        trigger: 'input[data-attribute_name="Beautiful Color"][data-value_name="' + nameGreen + '"]',
        run: 'click',
    },
    {
        content: "wait for variant to be loaded",
        trigger: '.oe_currency_value:contains("21.00")'
    },
    {
        content: "click on the image",
        trigger: imageSelector,
        run: 'clicknoleave',
    },
    {
        content: "check there is a zoom on that big image",
        trigger: '.o_wsale_image_viewer',
        run: () => {},
    },
]});
