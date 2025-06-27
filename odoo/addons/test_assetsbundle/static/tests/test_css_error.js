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
                const content = document.body.querySelector(".o_notification").innerText;
                if (!content.includes("The style compilation failed.")) {
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
                const content = document.body.querySelector(".o_notification").innerText;
                if (!content.includes("The style compilation failed.")) {
                    console.error("should contain a Style error notification");
                }
            },
        },
    ],
});
