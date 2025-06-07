import { registry } from "@web/core/registry";

const requestChatSteps = [
    {
        trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
        run: "click",
    },
    {
        trigger: ".o-livechat-root:shadow .o-mail-ChatWindow",
    },
];

registry.category("web_tour.tours").add("im_livechat_request_chat", {
    steps: () => requestChatSteps,
});

registry.category("web_tour.tours").add("im_livechat_request_chat_and_send_message", {
    steps: () => [
        ...requestChatSteps,
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit Hello, I need help please !",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains('Hello, I need help')",
        },
    ],
});
