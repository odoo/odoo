import { registry } from "@web/core/registry";
import * as tourUtils from "@website_sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("website_sale.check_free_delivery", {
    steps: () => [
        // Part 1: Check free delivery
        ...tourUtils.addToCartFromProductPage(),
        tourUtils.goToCart(),
        tourUtils.goToCheckout(),
        {
            trigger: "#o_delivery_methods label:text(Delivery Now Free Over 10)",
        },
        {
            content: "Check Free Delivery value to be zero",
            trigger: "#o_delivery_methods span:contains('0.0')",
            run: "click",
        },
        // Part 2: check multiple delivery & price loaded asynchronously
        {
            trigger: '#o_delivery_methods input[name="o_delivery_radio"]:checked',
        },
        {
            content: "Ensure price was loaded asynchronously",
            trigger:
                '#o_delivery_methods [name="o_delivery_method"]:contains("20.0"):contains("The Poste")',
        },
        tourUtils.confirmOrder(),
        ...tourUtils.payWithTransfer({ expectUnloadPage: true, waitFinalizeYourPayment: true }),
    ],
});
