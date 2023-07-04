/** @odoo-module **/
/**
 * Add custom steps to handle the optional products modal introduced
 * by the product configurator module.
 */
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import "@website_sale/../tests/tours/website_sale_buy";

patch(registry.category("web_tour.tours").get("shop_buy_product"), {
    steps() {
        const originalSteps = super.steps();
        const addCartStepIndex = originalSteps.findIndex((step) => step.id === "add_cart_step");
        originalSteps.splice(addCartStepIndex + 1, 1, {
            content: "click in modal on 'Proceed to checkout' button",
            trigger: 'button:contains("Proceed to Checkout")',
        });
        return originalSteps;
    },
});
