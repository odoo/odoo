(function () {
    'use strict';

    var website = openerp.website;

    website.Tour.ShopTest = website.Tour.extend({
        id: 'shop_buy_product',
        name: "Try to buy products",
        path: '/shop',
        testPath: '/shop',
        init: function () {
            var self = this;
            self.steps = [
                {
                    title:     "select ipod",
                    element:   '.oe_product_cart a:contains("iPod")',
                },
                {
                    title:     "select ipod 32Go",
                    element:   'input[name="product_id"]:not([checked])',
                },
                {
                    title:     "click on add to cart",
                    waitFor:   'input[name="product_id"]:eq(1)[checked]',
                    element:   'form[action="/shop/add_cart/"] .btn',
                },
                {
                    title:     "add suggested",
                    element:   'form[action="/shop/add_cart/"] .btn-link:contains("Add to Cart")',
                },
                {
                    title:     "add one more iPod",
                    waitFor:   '.my_cart_quantity:contains(2)',
                    element:   '#mycart_products tr:contains("iPod: 32 Gb") a.js_add_cart_json:eq(1)',
                },
                {
                    title:     "remove Headphones",
                    waitFor:   '#mycart_products tr:contains("iPod: 32 Gb") input.js_quantity[value=2]',
                    element:   '#mycart_products tr:contains("Apple In-Ear Headphones") a.js_add_cart_json:first',
                },
                {
                    title:     "set one iPod",
                    waitNot:   '#mycart_products tr:contains("Apple In-Ear Headphones")',
                    element:   '#mycart_products input.js_quantity',
                    sampleText: '1',
                },
                {
                    title:     "go to checkout",
                    waitFor:   '#mycart_products input.js_quantity[value=1]',
                    element:   'a[href="/shop/checkout/"]',
                },
                {
                    title:     "test with input error",
                    element:   'form[action="/shop/confirm_order/"] .btn:contains("Confirm")',
                    onload: function (tour) {
                        $("input[name='phone']").val("");
                    },
                },
                {
                    title:     "test without input error",
                    waitFor:   'form[action="/shop/confirm_order/"] .has-error',
                    element:   'form[action="/shop/confirm_order/"] .btn:contains("Confirm")',
                    onload: function (tour) {
                        if ($("input[name='name']").val() === "")
                            $("input[name='name']").val("website_sale-test-shoptest");
                        if ($("input[name='email']").val() === "")
                            $("input[name='email']").val("website_sale_test_shoptest@websitesaletest.optenerp.com");
                        $("input[name='phone']").val("123");
                        $("input[name='street']").val("123");
                        $("input[name='city']").val("123");
                        $("input[name='zip']").val("123");
                        $("select[name='country_id']").val("21");
                    },
                },
                {
                    title:     "select payment",
                    element:   '#payment_method label:has(img[title="transfer"]) input',
                },
                {
                    title:     "Pay Now",
                    waitFor:   '#payment_method label:has(input:checked):has(img[title="transfer"])',
                    element:   '.oe_sale_acquirer_button .btn[name="submit"]:visible',
                },
                {
                    title:     "finish",
                    waitFor:   '.oe_website_sale:contains("Thank you for your order")',
                }
            ];
            return this._super();
        },
    });
    // for test without editor bar
    website.Tour.add(website.Tour.ShopTest);

}());
