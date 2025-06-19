import { registry } from "@web/core/registry";
import { contains } from "@web/../tests/utils";

const messagesContain = (text) => `.o-livechat-root:shadow .o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat_chatbot_test_page_tour", {
    steps: () => [
        {
            trigger: messagesContain("Hello! I'm a bot!"),
            async run() {
                const ChatHub = this.anchor.closest(".o-mail-ChatHub");
                await contains(".o-mail-ChatWindow", {
                    text: "Testing Bot",
                    count: 1,
                    target: ChatHub,
                });
            },
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
            trigger: messagesContain("Hello! I'm a bot!"),
            async run() {
                const ChatHub = this.anchor.closest(".o-mail-ChatHub");
                await contains(".o-mail-ChatWindow", {
                    text: "Testing Bot",
                    count: 1,
                    target: ChatHub,
                });
            },
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
            trigger: ".o-livechat-root:shadow p:contains('Did we correctly answer your question?')",
            async run() {
                await contains("button", { target: this.anchor.getRootNode(), text: "Close" });
                await contains("button", {
                    target: this.anchor.getRootNode(),
                    text: "New Session",
                    count: 0,
                });
            },
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
