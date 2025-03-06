/** @odoo-module */

import { registry } from "@web/core/registry";

const commonSteps = [
    { trigger: ".o-livechat-root:shadow .o-mail-Message:contains('Hello! I'm a bot!')" },
    {
        trigger: ".o-livechat-root:shadow button:contains(I want to speak with an operator)",
        run: "click",
    },
];

registry.category("web_tour.tours").add("chatbot_fw_operator_matching_lang_en", {
    steps: () => [
        ...commonSteps,
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-NotificationMessage:contains(joined the channel)",
        },
    ],
});

registry.category("web_tour.tours").add("chatbot_fw_operator_matching_lang_fr", {
    steps: () => [
        ...commonSteps,
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-NotificationMessage:contains(a rejoint le canal)", // FIXME: lang is on behalf of who triggers the notification
        },
    ],
});
