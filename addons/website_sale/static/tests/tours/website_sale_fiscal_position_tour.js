odoo.define('website_sale_tour.website_sale_fiscal_position_tour', function (require) {
    'use strict';

    var tour = require("web_tour.tour");

    tour.register('website_sale_fiscal_position_portal_tour', {
        test: true,
        url: '/shop?search=Super%20Product'
    }, [
    {
        content: "Check price",
        trigger: ".oe_product:contains('Super product') .product_price:contains('80.00')",
        run: function() {} // Check
    },
    ]);

    tour.register('website_sale_fiscal_position_public_tour', {
        test: true,
        url: '/shop?search=Super%20Product'
    }, [
    {
        content: "Toggle Pricelist",
        trigger: ".o_pricelist_dropdown > .dropdown-toggle",
        run: 'click',
    },
    {
        content: "Change Pricelist",
        trigger: ".dropdown-item:contains('EUROPE EUR')",
        run: 'click',
    },
    {
        content: "Check price",
        trigger: ".oe_product:contains('Super product') .product_price:contains('92.00')",
        run: function() {} // Check
    },
    ]);
});
