import { registry } from "@web/core/registry";

const messagesContain = (text) => `.o-livechat-root:shadow .o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat_chatbot_test_page_tour", {
    steps: () => [
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-ChatHub:has(.o-mail-ChatWindow .o-mail-ChatWindow-header:text(Testing Bot)):count(1) .o-mail-Message-body:text(Hello! I'm a bot!)",
        },
        {
            trigger: messagesContain("I help lost visitors find their way."),
            run: "click",
        },
        {
            trigger: messagesContain("How can I help you?"),
            run: "click",
        },
        {
            trigger: '.o-livechat-root:shadow button:contains("I\'d like to buy the software")',
            run: "click",
        },
        {
            trigger: messagesContain("Can you give us your email please?"),
            run() {
                window.location.reload();
            },
            expectUnloadPage: true,
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-ChatHub:has(.o-mail-ChatWindow .o-mail-ChatWindow-header:text(Testing Bot)):count(1) .o-mail-Message-body:text(Hello! I'm a bot!)",
        },
        {
            trigger: '.o-livechat-root:shadow button:contains("Other & Documentation")',
            run: "click",
        },
        {
            trigger: messagesContain("Please find documentation at"),
            run: () => {},
        },
        {
            trigger: ".o-livechat-root:shadow [title='Close Chat Window (ESC)']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains('Yes, leave conversation')",
            run: "click",
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-ChatWindow:has(p:contains('Did we correctly answer your question?')):has(button:contains('Close')):not(:has(button:contains('New Session')))",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains('Close')",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-ChatHub:not(:visible)",
            content: "Livechat Button should not be visible",
        },
    ],
});
