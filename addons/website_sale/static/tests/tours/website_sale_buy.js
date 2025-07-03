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
<<<<<<< 3d4588798b4b52073d3b3e13c641ee70eb783709
        ...tourUtils.payWithTransfer({
            redirect: true,
            expectUnloadPage: true,
            waitFinalizeYourPayment: true,
        }),
||||||| 60ec0ba98a3f73d4720ca68c77ed4c69623ee08e
        ...tourUtils.payWithTransfer(true),
=======
        ...tourUtils.payWithTransfer({ redirect: true }),
>>>>>>> cbc9bdd12612311e69015b6fb3bbd59e5adba20b
    ]
});
