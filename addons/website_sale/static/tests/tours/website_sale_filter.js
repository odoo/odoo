odoo.define('website_sale.tour_filter', function (require) {
    'use strict';

    var tour = require("web_tour.tour");

    tour.register('website_sale_category_filter', {
        test: true,
        url: '/shop',
    }, [
    {
        content: "Open Customize menu",
        trigger: '#customize-menu > a:contains("Customize")',
    }, {
        content: "Enable Categories",
        trigger: 'a.dropdown-item label:contains("eCommerce Categories")',
    }, { // No Filter: All categories
        trigger: 'a:contains("(7)"):parent:contains("category_1")',
        run: function () {},
    }, {
        trigger: 'a:contains("(2)"):parent:contains("category_1_1")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_1_1_1")',
        run: function () {},
    }, {
        trigger: 'a:contains("(2)"):parent:contains("category_1_2")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_1_2_1")',
        run: function () {},
    }, {
        trigger: 'a:contains("(2)"):parent:contains("category_2")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_2_2")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_3")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_3_1")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_4")',
        run: function () {},
    }, { // Products in multiple child categories
        trigger: 'body',
        run: function () {
            window.location.href = window.location.origin + '/shop?search=product_d';
        },
    }, {
        trigger: 'a:contains("(2)"):parent:contains("category_1")',
        run: function () {},
    }, {
        trigger: 'a:contains("(2)"):parent:contains("category_1_1")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_1_1_1")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_2")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_2_2")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_3")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_3_1")',
        run: function () {},
    }, { // Products in multiple main categories
        trigger: 'body',
        run: function () {
            window.location.href = window.location.origin + '/shop?search=product_c';
        },
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_1")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_2")',
        run: function () {},
    }, { // Products in one child category
        trigger: 'body',
        run: function () {
            window.location.href = window.location.origin + '/shop?search=product_f';
        },
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_1")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_1_2")',
        run: function () {},
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_1_2_1")',
        run: function () {},
    }, { // Products in one main category
        trigger: 'body',
        run: function () {
            window.location.href = window.location.origin + '/shop?search=product_h';
        },
    }, {
        trigger: 'a:contains("(1)"):parent:contains("category_4")',
        run: function () {},
    }]);
});
