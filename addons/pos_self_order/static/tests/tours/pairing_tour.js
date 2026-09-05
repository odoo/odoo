import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

registry.category("web_tour.tours").add("pos_self_order_pairing_tour", {
    steps: () => [
        {
            content: "the pairing screen is displayed",
            trigger: ".pairing-panel:contains('Pair this kiosk')",
        },
        {
            content: "a non-empty pairing code is displayed",
            trigger: ".pairing-panel .pairing-code span:not(:empty)",
        },
        {
            content: "pairing code is validated by the admin",
            trigger: ".pairing-panel",
            expectUnloadPage: true,
            run: async () => {
                await rpc("/pos-self-order/test-approve-pairing", {
                    config_id: odoo.pos_config_id,
                });
            },
        },
        {
            content: "the kiosk is redirected to the ordering UI",
            trigger: ".btn:contains('Order Now')",
        },
    ],
});
