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
            trigger: '.o-livechat-root:shadow li:contains("I want to buy the software")',
            run: "click",
        },
        {
            trigger: messagesContain("Can you give us your email please?"),
            run() {
                window.location.reload();
            },
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
    ],
});
