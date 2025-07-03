import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale_cart_notification", {
    url: "/shop",
    steps: () => [
        ...tourUtils.addToCart({
            productName: "website_sale_cart_notification_product_1",
            expectUnloadPage: true,
        }),
        {
            content: "check that 1 website_sale_cart_notification_product_1 was added",
            trigger: '.toast-body span:contains("website_sale_cart_notification_product_1")',
        },
        {
            content: "check that 1 website_sale_cart_notification_product_1 was added",
            trigger: '.toast-body span:contains("1")',
        },
        {
            content: "check the price of 1 website_sale_cart_notification_product_1",
            trigger: '.toast-body div:contains("$ 1,000.00")',
        },
<<<<<<< 3d4588798b4b52073d3b3e13c641ee70eb783709
        ...tourUtils.searchProduct("website_sale_cart_notification_product_2", { select: true }),
||||||| 60ec0ba98a3f73d4720ca68c77ed4c69623ee08e
        {
            content: "close the notification",
            trigger: ".toast-header button.btn-close",
            run: "click",
        },
        {
            content: "check that the notification is closed",
            trigger: "div.position-fixed.w-100.h-100.top-0.pe-none",
            run() {
                if (this.anchor.querySelectorAll("div").length !== 1) {
                    console.error("The cart notification is not closed!");
                }
            },
        },
        ...tourUtils.searchProduct("website_sale_cart_notification_product_2"),
        {
            content: "select website_sale_cart_notification_product_2",
            trigger:
                '.oe_product_cart:first a:contains("website_sale_cart_notification_product_2")',
            run: "click",
        },
=======
        {
            content: "close the notification",
            trigger: ".toast-header button.btn-close",
            run: "click",
        },
        {
            content: "check that the notification is closed",
            trigger: "div.position-fixed.w-100.h-100.top-0.pe-none",
            run() {
                if (this.anchor.querySelectorAll("div").length !== 1) {
                    console.error("The cart notification is not closed!");
                }
            },
        },
        ...tourUtils.searchProduct("website_sale_cart_notification_product_2", { select: true }),
>>>>>>> cbc9bdd12612311e69015b6fb3bbd59e5adba20b
        {
            trigger: "#product_detail",
        },
        {
            content: "change quantity",
            trigger: '#product_detail form input[name=add_qty]',
            run: "edit 3",
        },
        {
            content: "click on add to cart",
            trigger: '#product_detail form #add_to_cart',
            run: "click",
        },
        {
            content: "check that 3 website_sale_cart_notification_product_2 was added",
            trigger: '.toast-body span:contains("website_sale_cart_notification_product_2")',
        },
        {
            content: "check that 3 website_sale_cart_notification_product_2 was added",
            trigger: '.toast-body span:contains("3")',
        },
        {
            content: "check that the novariants/custom attributes are displayed.",
            trigger: '.toast-body span.text-muted.small:contains("Size: S")',
        },
        {
            content: "check the price of 1 website_sale_cart_notification_product_2",
            trigger: '.toast-body div:contains("$ 15,000.00")',
        },
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
