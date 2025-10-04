/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('css_error_tour_frontend', {
    test: true,
    url: '/',
    steps: () => [
    {
        content: "Error message",
        trigger: ".o_notification.border-danger",
        run: () => {
            const title = document.body.querySelector(".o_notification .o_notification_title").innerText;
            if (!title.includes("Style error")) {
                throw new Error("should contain a Style error notification");
            }
        },
    },
]});
