/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("chatbot_fw_operator_matching_lang", {
    test: true,
    shadow_dom: ".o-livechat-root",
    steps: () => [
        {
            trigger: `.o-mail-Message:contains("Hello! I'm a bot!")`,
        },
        {
            trigger: "li:contains(I want to speak with an operator)",
            run: "click",
        },
        {
            trigger: ".o-mail-Composer-input:enabled",
            run: () => {},
        },
    ],
});
