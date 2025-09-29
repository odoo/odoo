import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('website_sale.basic_shop_flow', {
    url: '/shop',
    steps: () => [
        ...tourUtils.searchProduct("Storage Box", { select: true }),
        ...tourUtils.addToCartFromProductPage(),
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
