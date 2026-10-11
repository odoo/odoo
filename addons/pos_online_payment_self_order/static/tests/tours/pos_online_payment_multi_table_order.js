import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_online_payment_self_multi_company_payment", {
    steps: () => [
        {
            trigger: 'button[name="o_payment_submit_button"]:not(:disabled)',
        },
    ],
});
