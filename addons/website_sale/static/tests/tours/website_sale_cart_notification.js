import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale_cart_notification_tax_included", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({
            productName: "website_sale_cart_notification_product_1",
            expectUnloadPage: true,
        }),
        ...tourUtils.assertToastNotification({
            productName: "website_sale_cart_notification_product_1",
            qty: "1",
            price: "$ 1,150.00",
        }),
        ...tourUtils.searchProduct("website_sale_cart_notification_product_2", {
            select: true,
        }),
        {
            trigger: "#product_detail",
        },
        {
            content: "change quantity",
            trigger: "#product_detail form input[name=add_qty]",
            run: "edit 3",
        },
        {
            content: "click on add to cart",
            trigger: "#product_detail form #add_to_cart",
            run: "click",
        },
        ...tourUtils.assertToastNotification({
            productName: "website_sale_cart_notification_product_2",
            qty: "3",
            price: "$ 17,250.00",
            combinationName: "Size: S",
        }),
        {
            content: "Go To Cart",
            trigger: '.toast-body a:contains("View cart")',
            run: "click",
            expectUnloadPage: true,
        },
        ...tourUtils.assertCartContains({
            productName: "website_sale_cart_notification_product_1",
            backend: false,
        }),
        ...tourUtils.assertCartContains({
            productName: "website_sale_cart_notification_product_2",
            backend: false,
        }),
    ],
});

registry.category("web_tour.tours").add("website_sale_cart_notification_tax_excluded", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({
            productName: "website_sale_cart_notification_product_1",
            expectUnloadPage: true,
        }),
        ...tourUtils.assertToastNotification({
            productName: "website_sale_cart_notification_product_1",
            qty: "1",
            price: "$ 1,000.00",
        }),
        ...tourUtils.searchProduct("website_sale_cart_notification_product_2", {
            select: true,
        }),
        {
            trigger: "#product_detail",
        },
        {
            content: "change quantity",
            trigger: "#product_detail form input[name=add_qty]",
            run: "edit 3",
        },
        {
            content: "click on add to cart",
            trigger: "#product_detail form #add_to_cart",
            run: "click",
        },
        ...tourUtils.assertToastNotification({
            productName: "website_sale_cart_notification_product_2",
            qty: "3",
            price: "$ 15,000.00",
            combinationName: "Size: S",
        }),
        {
            content: "Go To Cart",
            trigger: '.toast-body a:contains("View cart")',
            run: "click",
            expectUnloadPage: true,
        },
        ...tourUtils.assertCartContains({
            productName: "website_sale_cart_notification_product_1",
            backend: false,
        }),
        ...tourUtils.assertCartContains({
            productName: "website_sale_cart_notification_product_2",
            backend: false,
        }),
    ],
});

registry
    .category("web_tour.tours")
    .add("website_sale_cart_notification_qty_and_total", {
        url: "/shop",
        steps: () => [
            ...tourUtils.addToCart({
                productName: "website_sale_cart_notification_product_1",
                expectUnloadPage: true,
            }),
            ...tourUtils.assertToastNotification({
                productName: "website_sale_cart_notification_product_1",
                qty: "1",
                price: "$ 1,000.00",
            }),
            // Again add same product
            {
                content: "change quantity",
                trigger: "#product_detail form input[name=add_qty]",
                run: "edit 3",
            },
            {
                content: "click on add to cart",
                trigger: "#product_detail form #add_to_cart",
                run: "click",
            },
            {
                content: "check that only newly added qty showing in the notification",
                trigger: '.toast-body span:contains("3")',
            },
            {
                content:
                    "check that price total only showing total of newly added quantity",
                trigger: '.toast-body div:contains("$ 3,000.00")',
            },
        ],
    });
