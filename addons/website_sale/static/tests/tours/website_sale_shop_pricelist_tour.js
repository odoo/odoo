odoo.define('website_sale_tour.website_sale_shop_pricelist_tour', function (require) {
    'use strict';

    var tour = require("web_tour.tour");

    tour.register('website_sale_shop_pricelist_tour', {
        test: true,
        url: '/shop'
    }, [
    {
        content: "Check pricelist",
        trigger: ".o_pricelist_dropdown:contains('Public Pricelist')",
        run: function() {} // Check
    },
    {
        content: "Go to login page",
        trigger: ".nav-link:contains('Sign in')"
    },
    {
        content: "Submit login",
        trigger: '.oe_login_form',
        run: function () {
            $('.oe_login_form input[name="login"]').val("toto");
            $('.oe_login_form input[name="password"]').val("long_enough_password");
            $('.oe_login_form input[name="redirect"]').val("/shop");
            $('.oe_login_form').submit();
        }
    },
    {
        content: "Check pricelist",
        trigger: ".o_pricelist_dropdown:contains('User Pricelist')",
        run: function() {} // Check
    },
    ]);
});
