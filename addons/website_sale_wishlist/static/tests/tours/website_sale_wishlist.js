import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { clickOnElement } from '@website/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_wishlist', {
    checkDelay: 250,
    url: '/shop?search=Customizable Desk',
    steps: () => [
        {
            content: "hover card && click on add to wishlist",
            trigger: ".o_wsale_product_grid_wrapper:contains(desk)",
            run: "hover && click .o_add_wishlist",
        },
        {
            trigger: 'a[href="/shop/wishlist"] .badge:contains(1)',
        },
        {
            content: "go to wishlist",
            trigger: 'a[href="/shop/wishlist"]',
            run: "click",
        },
        {
            content: "remove first item in whishlist",
            trigger: '.o_wish_rm:first',
            run: "click",
        },
        {
            content: "go back to the store",
            trigger: "a[href='/shop']",
            run: "click",
        },
        {
            content: "hover card && click on add to wishlist",
            trigger: ".o_wsale_product_grid_wrapper:contains(desk)",
            run: "hover && click .o_add_wishlist",
        },
        {
            trigger: ".my_wish_quantity:contains(1)",
        },
        {
            content: "check value of wishlist and go to login",
            trigger: 'a[href="/web/login"]',
            run: "click",
        },
        {
            content: "submit login",
            trigger: ".oe_login_form",
            run: function (){
                document.querySelector('.oe_login_form input[name="login"]').value = "admin";
                document.querySelector('.oe_login_form input[name="password"]').value = "admin";
                document.querySelector('.oe_login_form input[name="redirect"]').value = "/shop?search=Customizable Desk";
                document.querySelector(".oe_login_form").submit();
            },
        },
        {
            content: "check that logged in",
            trigger: "li span:contains('Mitchell Admin')",
        },
        {
            content: "click on Customizable Desk (TEST)",
            trigger: '.oe_product_cart a:contains("Customizable Desk")',
            run: "click",
        },
        {
            content: "check the first variant is already in wishlist",
            trigger: '#product_detail .o_add_wishlist_dyn:disabled',
        },
        {
            trigger: "#product_detail label:contains(Aluminium) input",
        },
        {
            content: "change variant",
            trigger: 'label:contains(Aluminium) input',
            run: "click",
        },
        {
            trigger: "#product_detail .o_add_wishlist_dyn:not(:disabled)",
        },
        {
            content: "wait button enable and click on add to wishlist",
            trigger: '#product_detail .o_add_wishlist_dyn',
            run: "click",
        },
        {
            trigger: 'a[href="/shop/wishlist"] .badge:contains(2)',
        },
        {
            content: "check that wishlist contains 2 items and go to wishlist",
            trigger: 'a[href="/shop/wishlist"]',
            run: "click",
        },
        {
            content: "remove Customizable Desk (TEST)",
            trigger: 'tr:contains("Customizable Desk") .o_wish_rm:first',
            run: "click",
        },
        {
            content: "check that wishlist contains 1 item",
            trigger: ".my_wish_quantity:contains(1)",
        },
        {
            content: "check B2B wishlist mode",
            trigger: "input#b2b_wish",
            run: "click",
        },
        {
            content: "add item to cart",
            trigger: '.o_wish_add:eq(1)',
            run: "click",
        },
        clickOnElement('Continue Shopping', 'button:contains("Continue Shopping")'),
        {
            content: "check that cart contains 1 item",
            trigger: ".my_cart_quantity:contains(1)",
        },
        {
            content: "check that wishlist contains 1 item",
            trigger: ".my_wish_quantity:contains(1)",
        },
        {
            content: "remove B2B wishlist mode",
            trigger: "input#b2b_wish",
            run: "click",
        },
        {
            content: "add last item to cart",
            trigger: '.o_wish_add:eq(1)',
            run: "click",
        },
        clickOnElement('Continue Shopping', 'button:contains("Continue Shopping")'),
        {
            content: "check that user is redirect - wishlist is empty",
            trigger: "#wrap #cart_products",
        },
        {
            content: "check that cart contains 2 items",
            trigger: ".my_cart_quantity:contains(2)",
        },
        {
            content: "check that wishlist is empty and no more visible",
            trigger: ":not(:has(.my_wish_quantity:visible))",
        },
        // Test dynamic attributes
        {
            content: "Create a product with dynamic attribute and its values.",
            trigger: 'body',
            run: function () {
                rpc("/web/dataset/call_kw/product.attribute/create", {
                    model: 'product.attribute',
                    method: 'create',
                    args: [{
                        'name': "color",
                        'display_type': 'color',
                        'create_variant': 'dynamic'
                    }],
                    kwargs: {},
                }).then(function (attributeId) {
                    return rpc("/web/dataset/call_kw/product.template/create", {
                        model: 'product.template',
                        method: 'create',
                        args: [{
                            'name': "Bottle",
                            'is_published': true,
                            'attribute_line_ids': [[0, 0, {
                                'attribute_id': attributeId,
                                'value_ids': [
                                    [0, 0, {
                                        'name': "red",
                                        'attribute_id': attributeId,
                                    }],
                                    [0, 0, {
                                        'name': "blue",
                                        'attribute_id': attributeId,
                                    }],
                                    [0, 0, {
                                        'name': "black",
                                        'attribute_id': attributeId,
                                    }],
                                ]
                            }]],
                        }],
                        kwargs: {},
                    });
                }).then(function () {
                    window.location.href = '/web/session/logout?redirect=/shop?search=Bottle';
                });
            },
        },
        {
            trigger: '.oe_product_cart:contains("Bottle")',
        },
        {
            content: "Add Bottle to wishlist from /shop",
            trigger: ".oe_product_cart:contains(Bottle)",
            run: "hover && click .oe_product_cart:contains(Bottle) .o_add_wishlist",
        },
        {
            content: "Check that wishlist contains 1 item",
            trigger: '.my_wish_quantity:contains(1)',
        },
        {
            trigger: '.oe_product_cart:contains("Bottle") .o_add_wishlist.disabled:not(:visible)',
        },
        {
            content: "Click on product",
            trigger: '.oe_product_cart a:contains("Bottle")',
            run: "click",
        },
        {
            content: "Select Bottle with second variant from /product",
            trigger: "input.js_variant_change[data-value_name=blue]:not(:visible)",
            run: "click",
        },
        {
            trigger: "#product_detail .o_add_wishlist_dyn:not(.disabled)",
        },
        {
            content: "Add product in wishlist",
            trigger: '#product_detail .o_add_wishlist_dyn',
            run: "click",
        },
        {
            content: "Select Bottle with third variant from /product",
            trigger: "input.js_variant_change[data-value_name=black]:not(:visible)",
            run: "click",
        },
        {
            trigger: "#product_detail .o_add_wishlist_dyn:not(.disabled)",
        },
        {
            content: "Add product in wishlist",
            trigger: '#product_detail .o_add_wishlist_dyn',
            run: "click",
        },
        {
            content: "Check that wishlist contains 3 items and go to wishlist",
            trigger: '.my_wish_quantity:contains(3)',
            run: function () {
                window.location.href = '/shop/wishlist';
            },
        },
        {
            content: "Check wishlist contains first variant",
            trigger: '#o_comparelist_table tr:contains("red")',
        },
        {
            content: "Check wishlist contains second variant",
            trigger: '#o_comparelist_table tr:contains("blue")',
        },
        {
            content: "Check wishlist contains third variant, then go to login",
            trigger: '#o_comparelist_table tr:contains("black")',
            run: function () {
                window.location.href = "/web/login";
            },
        },
        {
            content: "Submit login as admin",
            trigger: '.oe_login_form',
            run: function () {
                document.querySelector('.oe_login_form input[name="login"]').value = "admin";
                document.querySelector('.oe_login_form input[name="password"]').value = "admin";
                document.querySelector('.oe_login_form input[name="redirect"]').value = "/";
                document.querySelector(".oe_login_form").submit();
            },
        },
        // Test one impossible combination while other combinations are possible
        {
            content: "Archive the first variant",
            trigger: 'header#top:contains("Mitchell Admin")',
            run: function () {
                rpc("/web/dataset/call_kw/product.product/search", {
                    model: 'product.product',
                    method: 'search',
                    args: [[['name', '=', "Bottle"]]],
                    kwargs: {},
                })
                .then(function (productIds) {
                    return rpc("/web/dataset/call_kw/product.product/write", {
                        model: 'product.product',
                        method: 'write',
                        args: [productIds[0], {active: false}],
                        kwargs: {},
                    });
                })
                .then(function () {
                    window.location.href = '/web/session/logout?redirect=/shop?search=Bottle';
                });
            },
        },
        {
            trigger: ".js_sale",
        },
        {
            content: "Check there is wishlist button on product from /shop",
            trigger: ".oe_product_cart:contains(Bottle) .o_add_wishlist:not(:visible)",
        },
        {
            content: "Click on product",
            trigger: '.oe_product_cart a:contains("Bottle")',
            run: "click",
        },
        {
            content: "Select Bottle with first variant (red) from /product",
            trigger: "input.js_variant_change[data-value_name=red]:not(:visible)",
            run: "click",
        },
        {
            content: "Check there is no wishlist button when selecting impossible variant",
            trigger: '#product_detail:not(:has(.o_add_wishlist))',
        },
        {
            content: "Select Bottle with second variant (blue) from /product",
            trigger: "input.js_variant_change[data-value_name=blue]:not(:visible)",
            run: "click",
        },
        {
            content: "Click on wishlist when selecting a possible variant from /product",
            trigger: '#product_detail .o_add_wishlist_dyn:not(.disabled)',
            run: "click",
        },
        {
            content: "Check product added to wishlist and go to login",
            trigger: '.my_wish_quantity:contains(1)',
            run: function () {
                window.location.href = "/web/login";
            },
        },
        {
            content: "Submit login",
            trigger: '.oe_login_form',
            run: function () {
                document.querySelector('.oe_login_form input[name="login"]').value = "admin";
                document.querySelector('.oe_login_form input[name="password"]').value = "admin";
                document.querySelector('.oe_login_form input[name="redirect"]').value = "/";
                document.querySelector(".oe_login_form").submit();
            },
        },
        // test when all combinations are impossible
        {
            content: "Archive all variants",
            trigger: 'header#top:contains("Mitchell Admin")',
            run: function () {
                rpc("/web/dataset/call_kw/product.product/search", {
                    model: 'product.product',
                    method: 'search',
                    args: [[['name', '=', "Bottle"]]],
                    kwargs: {},
                })
                .then(function (productIds) {
                    return rpc("/web/dataset/call_kw/product.product/write", {
                        model: 'product.product',
                        method: 'write',
                        args: [productIds, {active: false}],
                        kwargs: {},
                    });
                })
                .then(function () {
                    window.location.href = '/web/session/logout?redirect=/shop?search=Bottle';
                });
            }
        },
        {
            trigger: ".js_sale",
        },
        {
            content: "Check that there is no wishlist button from /shop",
            trigger: '.oe_product_cart:contains("Bottle"):not(:has(.o_add_wishlist))',
        },
        {
            content: "Click on product",
            trigger: '.oe_product_cart a:contains("Bottle")',
            run: "click",
        },
        {
            content: "Check that there is no wishlist button from /product",
            trigger: '#product_detail:not(:has(.o_add_wishlist_dyn))',
        },
        // Test if the wishlist button is active or not in /shop
        {
            content: "Go to '/shop?search=Customizable Desk'",
            trigger: 'body',
            run: function () {
                window.location.href = '/shop?search=Customizable Desk '
            },
        },
        {
            content: "Click on the product",
            trigger: '.oe_product_image_link img',
            run: "click",
        },
        {
            content: "Add the product in the wishlist",
            trigger: '#product_option_block .o_add_wishlist_dyn',
            run: "click",
        },
        {
            content: "Added into the wishlist",
            trigger: '.my_wish_quantity.bg-primary:contains(1)',
        },
        {
            content: "Go to '/shop",
            trigger: 'header#top a[href="/shop"]',
            run: "click",
        },
        {
            content: "Search the product Customizable Desk'",
            trigger: 'form.o_wsale_products_searchbar_form input',
            run: function () {
                document.querySelector(
                    'form.o_wsale_products_searchbar_form input[name="search"]'
                ).value = "Customizable Desk";
                document.querySelector("form.o_wsale_products_searchbar_form button").click();
            },
        },
        {
            content: "The product is in the wishlist",
            trigger: '.oe_product_cart .o_wsale_product_information:has(.o_add_wishlist[disabled])',
        },
        {
            content: "Go to the wishlist",
            trigger: 'a[href="/shop/wishlist"]',
            run: "click",
        },
        {
            content: "Remove the product from the wishlist",
            trigger: '.o_wish_rm',
            run: "click",
        },
        {
            content: "Go to '/shop",
            trigger: 'header#top a[href="/shop"]',
            run: "click",
        },
        {
            content: "Search the product Customizable Desk'",
            trigger: 'form.o_wsale_products_searchbar_form input',
            run: function () {
                document.querySelector(
                    'form.o_wsale_products_searchbar_form input[name="search"]'
                ).value = "Customizable Desk";
                document.querySelector("form.o_wsale_products_searchbar_form button").click();
            },
        },
        {
            content: "The product is not in the wishlist",
            trigger: '.oe_product_cart .o_wsale_product_information:not(:has(.o_add_wishlist[disabled]))',
        },
    ]
});
