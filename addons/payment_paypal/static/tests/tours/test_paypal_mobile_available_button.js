import { waitUntil } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_paypal_mobile_available_button', {
    steps: () => [
        {
            content: "Select PayPal payment method",
            trigger: '[name="o_payment_radio"][data-provider-code="paypal"]',
            async run() {
                try {
                    document.querySelector('[name="o_payment_radio"][data-provider-code="paypal"]')
                        .click();
                    await waitUntil(() => {
                        return document.getElementById("o_paypal_button_container_inactive")
                            && document.getElementById("o_paypal_button_container");
                    }, { timeout: 1000 });
                } catch (error) {
                    // PayPal SDK will not be loaded with credentials, handle the error gracefully
                    console.error("Error selecting PayPal payment method:", error);
                }
            },
        },
    ],
});
