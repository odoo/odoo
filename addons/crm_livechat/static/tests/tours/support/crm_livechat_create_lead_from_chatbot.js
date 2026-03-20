import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("crm_livechat.create_lead_from_chatbot", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Hello, how can I help you?)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit I'd like to know more about the CRM application.",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-Message:contains(Would you mind leaving your email address so that we can reach you back?)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit visitor@example.com",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-Message:contains(Thank you, you should hear back from us very soon!)",
        },
    ],
});
