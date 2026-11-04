import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.lazy_frontend_bus", {
    url: "/",
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            async run() {
                await odoo.__WOWL_DEBUG__.root.env.services["mail.store"].isReady;
                if (odoo.__WOWL_DEBUG__.root.env.services.bus_service.isActive) {
                    throw new Error("Bus service should not start when loading the page");
                }
            },
        },
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit Hello, I need help!",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run(helpers) {
                if (odoo.__WOWL_DEBUG__.root.env.services.bus_service.isActive) {
                    throw new Error("Bus service should not start for temporary live chat");
                }
                helpers.press("Enter");
            },
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Hello, I need help!)",
            run() {
                if (!odoo.__WOWL_DEBUG__.root.env.services.bus_service.isActive) {
                    throw new Error("Bus service should start after first live chat message");
                }
            },
        },
    ],
});
