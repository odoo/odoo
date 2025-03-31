/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("css_error_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Error message",
            trigger: ".o_notification:has(.o_notification_bar.bg-danger)",
        },
        {
            trigger: "body",
            run: () => {
                const title = document.body.querySelector(
                    ".o_notification .o_notification_title"
                ).innerText;
                if (!title.includes("Style error")) {
                    console.error("should contain a Style error notification");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("css_error_tour_frontend", {
    url: "/",
    steps: () => [
        {
            content: "Error message",
            trigger: ".o_notification:has(.o_notification_bar.bg-danger)",
        },
        {
            trigger: "body",
            run: () => {
                const title = document.body.querySelector(
                    ".o_notification .o_notification_title"
                ).innerText;
                if (!title.includes("Style error")) {
                    console.error("should contain a Style error notification");
                }
            },
        },
    ],
});
