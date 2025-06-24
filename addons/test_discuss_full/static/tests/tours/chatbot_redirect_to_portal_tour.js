import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_mail_full.chatbot_redirect_to_portal", {
    url: "/contactus",
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-Message:contains(Hello, were do you want to go?)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow li:contains(Go to the portal page)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains('Go to the portal page')",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:last:contains('Tadam')",
        },
    ],
});
