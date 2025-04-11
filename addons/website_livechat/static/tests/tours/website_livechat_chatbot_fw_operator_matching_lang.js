/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("chatbot_fw_operator_matching_lang", {
    steps: () => [
        { trigger: ".o-livechat-root:shadow .o-mail-Message:contains('Hello! I'm a bot!')" },
        {
<<<<<<< 042a54e418dcdd4834930d3fd87889273a1e0cee
            trigger: ".o-livechat-root:shadow button:contains(I want to speak with an operator)",
            run: "click",
        },
        {
            // Wait for the operator to be added: composer is only enabled at that point.
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input:enabled",
||||||| 0812adedeea4edd70d57861f40248df4729086a0
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
=======
            trigger:
                ".o-livechat-root:shadow .o-mail-NotificationMessage:contains(invited @Operator en_US to the channel)",
        },
    ],
});

registry.category("web_tour.tours").add("chatbot_fw_operator_matching_lang_fr", {
    steps: () => [
        ...commonSteps,
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-NotificationMessage:contains(@Operator fr_FR invité au canal)", // FIXME: lang is on behalf of who triggers the notification
>>>>>>> 74457abf0511701134c04044712981f1145b5d67
        },
    ],
});
