/* @odoo-module */

import { registry } from "@web/core/registry";

import wTourUtils from "website.tour_utils";

registry.category("web_tour.tours").add("test_hide_chat_window_on_preview", {
    test: true,
    steps: [
        {
            trigger: ".o-mail-ChatWindow",
            run() {
                window.location.href = wTourUtils.getClientActionUrl("/");
            },
        },
        {
            trigger: ".o_website_preview",
            run() {
                if (document.querySelector(".o-mail-ChatWindow")) {
                    throw new Error("Chat window should not be visible");
                }
            },
        },
    ],
});
