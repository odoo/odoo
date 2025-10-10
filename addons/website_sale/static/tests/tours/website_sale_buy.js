import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('shop_buy_product', {
    url: '/shop',
    steps: () => [
        ...tourUtils.searchProduct("Storage Box", { select: true }),
        {
            content: "click on add to cart",
            trigger: '#product_detail form #add_to_cart',
            run: "click",
        },
        tourUtils.goToCart(),
        tourUtils.goToCheckout(),
        tourUtils.confirmOrder(),
        ...tourUtils.payWithTransfer({
            redirect: true,
            expectUnloadPage: true,
            waitFinalizeYourPayment: true,
        }),
    ]
});

registry.category("web_tour.tours").add('shop_repair_product', {
    url: '/shop',
    steps: () => [
        ...tourUtils.searchProduct("Test Repair Service", { select: true }),
        {
            content: "click on add to cart",
            trigger: '#product_detail form #add_to_cart',
            run: "click",
        },
        tourUtils.goToCart(),
    ]
});
