import { registry } from "@web/core/registry";
import { contains } from "@web/../tests/utils";

const messagesContain = (text) => `.o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat_chatbot_test_page_tour", {
    shadow_dom: ".o-livechat-root",
    steps: () => [
        {
            trigger: messagesContain("Hello! I'm a bot!"),
            async run() {
                const chatWindowContainer = this.anchor.closest(".o-mail-ChatWindowContainer");
                await contains(".o-mail-ChatWindow", {
                    text: "Testing Bot",
                    count: 1,
                    target: chatWindowContainer,
                });
            },
        },
        {
            trigger: messagesContain("I help lost visitors find their way."),
        },
        {
            trigger: messagesContain("How can I help you?"),
        },
        {
            trigger: 'li:contains("I want to buy the software")',
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
                const chatWindowContainer = this.anchor.closest(".o-mail-ChatWindowContainer");
                await contains(".o-mail-ChatWindow", {
                    text: "Testing Bot",
                    count: 1,
                    target: chatWindowContainer,
                });
            },
        },
    ],
});
