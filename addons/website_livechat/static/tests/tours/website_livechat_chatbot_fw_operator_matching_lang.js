/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("chatbot_fw_operator_matching_lang", {
    steps: () => [
        { trigger: ".o-livechat-root:shadow .o-mail-Message:contains('Hello! I'm a bot!')" },
        {
            trigger: ".o-livechat-root:shadow button:contains(I want to speak with an operator)",
            run: "click",
        },
        {
            // Wait for the operator to be added: composer is only enabled at that point.
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input:enabled",
        },
    ],
});
