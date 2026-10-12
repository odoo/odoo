import { postMessage, waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";
import { Chatbot } from "@im_livechat/core/common/chatbot_model";

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

registry.category("web_tour.tours").add("website_livechat.chatbot_continue_after_login_tour", {
    steps: () => {
        patch(Chatbot, {
            MESSAGE_DELAY: 0,
            TYPING_DELAY: 0,
        });
        return [
            waitForMessage("Hello! I'm a bot!"),
            waitForMessage("I help lost visitors find their way."),
            waitForMessage("How can I help you?"),
            {
                trigger: '.o-livechat-root:shadow button:text("I\'d like to buy the software")',
                run: "click",
            },
            waitForMessage("Can you give us your email please?"),
            {
                trigger: "a.o_nav_link_btn:text(Sign in)",
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: ".oe_login_form input#login",
                run: "edit portal_user",
            },
            {
                trigger: ".oe_login_form input#password",
                run: "edit portal_user",
            },
            {
                trigger: ".oe_login_form button[type='submit']",
                run: "click",
                expectUnloadPage: true,
            },
            {
                trigger: ".o_portal_wrap h1:text(My account)",
            },
            {
                trigger:
                    ".o-livechat-root:shadow .o-mail-NotificationMessage:has(:text('Albert authenticated as Batman.'))",
            },
            waitForMessage("I'd like to buy the software", { selfAuthored: true }),
            ...postMessage("abc@email.com"),
            waitForMessage("Your email is validated, thank you!"),
            {
                trigger: ".o-livechat-root:shadow .o-mail-Message:count(7)",
            },
        ];
    },
});
