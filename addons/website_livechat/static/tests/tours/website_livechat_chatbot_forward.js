import { registry } from "@web/core/registry";

const messagesContain = (text) => `.o-livechat-root:shadow .o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat.chatbot_forward", {
    url: "/",
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: messagesContain("Hello, what can I do for you?"),
        },
        {
            trigger: ".o-livechat-root:shadow button:contains(Forward to operator)",
            run: "click",
        },
        {
            trigger: messagesContain("I'll forward you to an operator."),
        },
        {
<<<<<<< 042a54e418dcdd4834930d3fd87889273a1e0cee
            // Wait for the operator to be added: composer is only enabled at that point.
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input:enabled",
||||||| 0812adedeea4edd70d57861f40248df4729086a0
            trigger:
                ".o-livechat-root:shadow .o-mail-NotificationMessage:contains(joined the channel)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
=======
            trigger:
                ".o-livechat-root:shadow .o-mail-NotificationMessage:contains(invited @El Deboulonnator to the channel)",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
>>>>>>> 74457abf0511701134c04044712981f1145b5d67
            run: "edit Hello, I need help!",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: messagesContain("Hello, I need help!"),
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input:enabled",
        },
    ],
});
