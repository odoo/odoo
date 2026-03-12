import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale.update_cart", {
    steps: () => [
        ...tourUtils.searchProduct("conference chair", { select: true }),
        {
            trigger: "#product_detail",
        },
        {
            content: "select Conference Chair Aluminium",
            trigger: "label:contains(Aluminium) input",
            run: "click",
        },
        {
            trigger: "#product_detail",
        },
        {
            content: "select Conference Chair Steel",
            trigger: "label:contains(Steel) input",
            run: "click",
        },
        {
            trigger: "label:contains(Steel) input:checked",
        },
        ...tourUtils.addToCartFromProductPage(),
        {
            content: "click in modal on 'Proceed to checkout' button",
            trigger: 'button:contains("Checkout")',
            run: "click",
            expectUnloadPage: true,
        },
        ...tourUtils.assertCartContains({
            productName: "Conference Chair",
            combinationName: "Steel",
        }),
        {
            content: "add suggested",
            trigger: '#suggested_products div:has(a:contains("Storage Box")) button:contains("Add to cart")',
            run: "click",
        },
        {
            trigger: '#cart_products a[name="o_cart_line_product_link"]>h6:contains("Storage Box")',
        },
        {
            content: "remove Storage Box",
            trigger:
                '#cart_products div.o_cart_product:contains("Storage Box") button[name="remove_quantity"]',
            run: "click",
        },
        {
            trigger:
                '#wrap:not(:has(#suggested_products a[name="o_cart_line_product_link"]>h6:contains("Storage Box")))',
        },
        {
            content: "add one more",
            trigger:
                '#cart_products div.o_cart_product:contains("Conference Chair") button[name="add_quantity"]',
            run: "click",
        },
        ...tourUtils.assertCartContains({
            productName: "Conference Chair",
            combinationName: "Steel",
            quantity: 2,
        }),
        {
            content: "set one",
            trigger: "#cart_products input.js_quantity",
            run: "edit 1",
        },
    ],
});
