/* @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mail_message_load_order_tour", {
    test: true,
    steps: () => [
        {
            trigger: ".o-mail-DiscussSidebarChannel:contains(MyTestChannel)",
            run: "click",
        },
        {
            trigger: "*[title='Pinned Messages']",
            run: "click",
        },
        {
            trigger: ".o-mail-MessageCard-jump",
            run: "click",
        },
        {
            // Messages depends on FETCH_LIMIT (currently set to 30) in
            // the thread service. Thus, at first load the message range
            // will be (31 - 60). This trigger ensures the next messages
            // are fetched after jumping to the message.
            trigger: ".o-mail-Thread .o-mail-Message:first:not(:contains(31))",
            async run() {
                // ensure 1 - 16 are loaded in order: 15 below and the
                // one we're loading messages around.
                const messages = Array.from(
                    document.querySelectorAll(".o-mail-Thread .o-mail-Message-content")
                ).map((el) => el.innerText);
                for (let i = 0; i < 16; i++) {
                    if (messages[i] !== (i + 1).toString()) {
                        throw new Error("Wrong message order after loading around");
                    }
                }
                const thread = document.querySelector(".o-mail-Thread");
                thread.scrollTop = thread.scrollHeight - thread.clientHeight;
            },
        },
        {
            // After jumping to the pinned message, the message range
            // was (1 -16): 15 before (but none were found), 15 after
            // and the pinned message itself. This trigger ensures the
            // next messages are fetched after scrolling to the bottom.
            trigger: ".o-mail-Thread .o-mail-Message:contains(17)",
            run() {
                // ensure 1 - 46  are loaded in order.
                const messages = Array.from(
                    document.querySelectorAll(".o-mail-Thread .o-mail-Message-content")
                ).map((el) => el.innerText);
                for (let i = 0; i < 46; i++) {
                    if (messages[i] !== (i + 1).toString()) {
                        throw new Error("Wrong message order after loading after");
                    }
                }
                const thread = document.querySelector(".o-mail-Thread");
                thread.scrollTop = thread.scrollHeight - thread.clientHeight;
            },
        },
    ],
});
