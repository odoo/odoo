/* @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.lazy_frontend_bus", {
    test: true,
    url: "/",
    steps: () => [
        {
            trigger: "body",
            async run() {
                await odoo.__WOWL_DEBUG__.root.env.services["mail.messaging"].isReady;
                if (odoo.__WOWL_DEBUG__.root.env.services.bus_service.isActive) {
                    throw new Error("Bus service should not be started eagerly");
                }
            },
        },
    ],
});
