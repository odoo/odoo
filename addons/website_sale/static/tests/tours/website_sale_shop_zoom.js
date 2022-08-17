odoo.define('website_sale.tour_shop_zoom', function (require) {
'use strict';

var tour = require('web_tour.tour');

var imageSelector = '#o-carousel-product .carousel-item.active img';
var imageName = "A Colorful Image";
var nameGreen = "Forest Green";

// This tour relies on a data created from the python test.
tour.register('shop_zoom', {
    test: true,
    url: '/shop?search=' + imageName,
},
[
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
]);
});
