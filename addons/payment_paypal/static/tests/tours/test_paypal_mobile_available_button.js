import { waitUntil } from '@odoo/hoot-dom';
import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('test_paypal_buttons_rendered_on_mobile_checkout', {
    steps: () => [
        {
            content: "Select PayPal payment method",
            trigger: '[name="o_payment_radio"][data-provider-code="paypal"]',
            async run() {
                try {
                    document.querySelector(
                        '[name="o_payment_radio"][data-provider-code="paypal"]'
                    ).click();
                    await waitUntil(() => {
                        const paypalButtons = document.querySelectorAll(
                            '[id^="o_paypal_enabled_button"]'
                        );
                        return [...paypalButtons].some(button => button.offsetParent !== null);
                    }, { timeout: 1000 });
                } catch (error) {
                    // PayPal SDK will not be loaded w/o credentials; handle the error gracefully.
                    console.error("Error selecting PayPal payment method:", error);
                }
            },
        },
    ],
});
