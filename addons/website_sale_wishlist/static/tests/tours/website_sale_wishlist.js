import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale_wishlist/../tests/tours/tour_utils";

registry.category("web_tour.tours").add('website_sale_wishlist.wishlist_updates', {
    url: '/shop?search=Customizable Desk',
    steps: () => [
        ...tourUtils.addToWishlistFromShopPage(),
        tourUtils.goToWishlist({ quantity: 1 }),
        {
            content: "remove first item in whishlist",
            trigger: '.o_wish_rm:first',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "hover card && click on add to wishlist",
            trigger: ".o_wsale_product_grid_wrapper:contains(desk)",
            run: "hover && click .o_add_wishlist",
        },
        tourUtils.assertWishlistQuantity(1),
        {
            content: "check value of wishlist and go to login",
            trigger: 'a[href="/web/login"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "submit login",
            trigger: ".oe_login_form",
            run: function () {
                document.querySelector('.oe_login_form input[name="login"]').value = "admin";
                document.querySelector('.oe_login_form input[name="password"]').value = "admin";
                document.querySelector('.oe_login_form input[name="redirect"]').value = "/shop?search=Customizable Desk";
                document.querySelector(".oe_login_form").submit();
            },
            expectUnloadPage: true,
        },
        {
            content: "check that logged in",
            trigger: "li span:contains('Mitchell Admin')",
        },
        {
            content: "click on Customizable Desk (TEST)",
            trigger: '.oe_product_cart a:contains("Customizable Desk")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "check the first variant is already in wishlist",
            trigger: '#product_detail .o_add_wishlist_dyn.disabled',
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
            trigger: "#product_detail .o_add_wishlist_dyn:not(.disabled)",
        },
        {
            content: "wait button enable and click on add to wishlist",
            trigger: '#product_detail .o_add_wishlist_dyn',
            run: "click",
        },
        tourUtils.goToWishlist({ quantity: 2}),
        {
            content: "remove Customizable Desk (TEST)",
            trigger: '.o_wish_rm:first',
            run: "click",
        },
        tourUtils.assertWishlistQuantity(1),
        {
            content: "add last item to cart",
            trigger: '.o_wish_add:eq(1)',
            run: "click",
        },
        {
            content: "Clicking on Add to cart",
            trigger: "button[name='website_sale_product_configurator_continue_button']",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "check that user is redirect - wishlist is empty",
            trigger: "#wrap #cart_products",
        },
        {
            content: "check that cart contains 1 item",
            trigger: ".my_cart_quantity:contains(1)",
        },
        {
            content: "check that wishlist is empty and no more visible",
            trigger: ":not(:has(.my_wish_quantity:visible))",
        },
        // Test if the wishlist button is active or not in /shop
        {
            content: "Go to '/shop?search=Customizable Desk'",
            trigger: 'body',
            run: function () {
                window.location.href = '/shop?search=Customizable Desk '
            },
            expectUnloadPage: true,
        },
        {
            content: "Click on the product",
            trigger: '.oe_product_image_link img',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Add the product in the wishlist",
            trigger: '#product_option_block .o_add_wishlist_dyn',
            run: "click",
        },
        tourUtils.assertWishlistQuantity(1),
        {
            content: "Go to '/shop",
            trigger: 'header#top a[href="/shop"]',
            run: "click",
            expectUnloadPage: true,
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
            expectUnloadPage: true,
        },
        {
            content: "The product is in the wishlist",
            trigger: '.oe_product_cart .o_wsale_product_btn:has(.o_add_wishlist[disabled])',
        },
        {
            content: "Go to the wishlist",
            trigger: 'a[href="/shop/wishlist"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Remove the product from the wishlist",
            trigger: '.o_wish_rm',
            run: "click",
            expectUnloadPage: true,
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
            expectUnloadPage: true,
        },
        {
            content: "The product is not in the wishlist",
            trigger: '.oe_product_cart .o_wsale_product_btn:not(:has(.o_add_wishlist[disabled]))',
        },
    ]
});


registry.category("web_tour.tours").add('website_sale_wishlist.dynamic_variants', {
    url: '/shop?search=Bottle',
    steps: () => [
        {
            trigger: '.oe_product_cart:contains("Bottle")',
        },
        ...tourUtils.addToWishlistFromShopPage(),
        tourUtils.assertWishlistQuantity(1),
        {
            content: "Click on product",
            trigger: '.oe_product_cart a:contains("Bottle")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Select Bottle with second variant from /product",
            trigger: "input.js_variant_change[data-value-name=blue]:not(:visible)",
            run: "click",
        },
        ...tourUtils.addToWishlistFromProductPage(),
        tourUtils.assertWishlistQuantity(2),
        {
            content: "Select Bottle with third variant from /product",
            trigger: "input.js_variant_change[data-value-name=black]:not(:visible)",
            run: "click",
        },
        ...tourUtils.addToWishlistFromProductPage(),
        tourUtils.goToWishlist({ quantity: 3}),
        {
            content: "Check wishlist contains first variant",
            trigger: '#o_comparelist_table .oe_product_cart a:contains("red")',
        },
        {
            content: "Check wishlist contains second variant",
            trigger: '#o_comparelist_table .oe_product_cart a:contains("blue")',
        },
        {
            content: "Check wishlist contains third variant, then go to login",
            trigger: '#o_comparelist_table .oe_product_cart a:contains("black")',
        },
    ]
});

registry.category("web_tour.tours").add('website_sale_wishlist.archived_variant', {
    url: '/shop?search=Bottle',
    steps: () => [
        {
            trigger: ".js_sale",
        },
        {
            content: "Check there is wishlist button on product from /shop",
            trigger: ".o_wsale_product_grid_wrapper:contains(Bottle) .o_add_wishlist",
        },
        {
            content: "Click on product",
            trigger: '.oe_product_cart a:contains("Bottle")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Select Bottle with first variant (red) from /product",
            trigger: "input.js_variant_change[data-value-name=red]:not(:visible)",
            run: "click",
        },
        {
            content: "Check there is no wishlist button when selecting impossible variant",
            trigger: '#product_detail:not(:has(.o_add_wishlist))',
        },
        {
            content: "Select Bottle with second variant (blue) from /product",
            trigger: "input.js_variant_change[data-value-name=blue]:not(:visible)",
            run: "click",
        },
        ...tourUtils.addToWishlistFromProductPage(),
        tourUtils.assertWishlistQuantity(1),
    ]
});

registry.category("web_tour.tours").add('website_sale_wishlist.no_valid_combination', {
    steps: () => [
        {
            content: "Check that there is no wishlist button on the product page",
            trigger: '#product_detail:not(:has(.o_add_wishlist_dyn))',
        },
    ],
});