/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.chatbot_restore_state_tour", {
    test: true,
    url: "/contactus",
    shadow_dom: ".o-livechat-root",
    steps: () => [
        {
            trigger: ".o-livechat-LivechatButton",
        },
        {
            trigger: ".o-mail-Message:contains(How can I help you?)",
            run: () => {
                const chatbotService = odoo.__WOWL_DEBUG__.root.env.services["im_livechat.chatbot"];
                if (chatbotService.isRestoringSavedState) {
                    throw new Error(
                        "Chatbot should not be restoring state at this stage."
                    );
                }
            },
        },
    ],
});
