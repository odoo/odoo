/** @odoo-module **/

import { registry } from "@web/core/registry";

var imageSelector = '#o-carousel-product .carousel-item.active img';
var imageName = "A Colorful Image";
var nameGreen = "Forest Green";

// This tour relies on a data created from the python test.
registry.category("web_tour.tours").add('shop_zoom', {
    url: '/shop?debug=1&search=' + imageName,
    steps: () => [
    {
        content: "select " + imageName,
        trigger: `.oe_product_cart a:text(${imageName})`,
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "click on the image",
        trigger: imageSelector,
        run: "click",
    },
    {
        content: "check that the image viewer opened",
        trigger: '.o_wsale_image_viewer',
    },
    {
        content: "close the image viewer",
        trigger: '.o_wsale_image_viewer_header span.fa-times',
        run: "click",
    },
    {
        content: "change variant",
        trigger: `input[data-attribute_name='Beautiful Color'][data-value_name='${nameGreen}']:not(:visible)`,
        run: 'click',
    },
    {
        content: "wait for variant to be loaded",
        trigger: '.oe_currency_value:contains("21.00")',
        run: "click",
    },
    {
        content: "click on the image",
        trigger: imageSelector,
        run: "click",
    },
    {
        content: "check there is a zoom on that big image",
        trigger: '.o_wsale_image_viewer',
    },
]});

registry.category("web_tour.tours").add("shop_zoom_grid_image_order", {
    steps: () => [
        {
            content: "check that the product page is in grid layout",
            trigger: "#o-grid-product",
        },
        {
            content: "open the image viewer from the third image in visual order",
            trigger:
                ".o_wsale_product_page_grid_column:nth-child(2) .product_detail_img[alt='image 3']",
            run: "click",
        },
        {
            content: "verify that the viewer opens at the third position (matching visual order)",
            trigger: ".o_wsale_image_viewer_carousel li:nth-child(3).active",
        },
    ],
});
