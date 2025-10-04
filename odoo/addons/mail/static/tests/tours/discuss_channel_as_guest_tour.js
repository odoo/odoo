/* @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_channel_as_guest_tour.js", {
        test: true,
        steps: () => [
            {
                content: "Channel secret token has been hidden on welcome page",
                trigger: ".o-mail-WelcomePage",
                run() {
                    if (!window.location.pathname.startsWith("/discuss/channel")) {
                        console.error("Channel secret token is still present in URL.");
                    }
                },
            },
            {
                content: "Click join",
                trigger: "button[title='Join Channel']",
                extraTrigger: ".o-mail-Thread",
            },
            {
                content: "Check that we are on channel page",
                trigger: ".o-mail-Thread",
                run() {},
            },
        ],
    });
