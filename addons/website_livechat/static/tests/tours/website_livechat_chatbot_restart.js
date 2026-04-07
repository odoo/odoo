import { registry } from "@web/core/registry";

const stepsUntilLastMessage = [
    {
        trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Enter your email address)",
    },
    {
        trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
        run: "edit test@example.com",
    },
    {
        trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
        run: "press Enter",
    },
    {
        trigger:
            ".o-livechat-root:shadow .o-mail-Message:contains(Do you want to restart the conversation?)",
    },
];

registry.category("web_tour.tours").add("website_livechat.chatbot_restart_on_feedback_tour", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        ...stepsUntilLastMessage,
        // restart in chat window
        {
            trigger: ".o-livechat-root:shadow button:contains(Yes, restart please.)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
            run: "click",
        },
        ...stepsUntilLastMessage,
        // restart in feedback
        {
            trigger: ".o-livechat-root:shadow button:contains(Yes, restart please.)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains(Continue)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow div:contains(Did we correctly answer your question?)",
        },
        {
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
            run: "click",
        },
        ...stepsUntilLastMessage,
        // restart not displayed as chatbot did not finish
        {
            trigger: ".o-livechat-root:shadow button[title='Close Chat Window (ESC)']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains(Yes, leave conversation)",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow div:contains(Did we correctly answer your question?)",
        },
        {
            trigger:
                '.o-livechat-root:shadow .o-mail-ChatWindow-header:not(:has(button[title="Restart Conversation"]))',
        },
    ],
});
