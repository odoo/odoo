/* @odoo-module */

import { registry } from "@web/core/registry";
import { contains, scroll } from "@web/../tests/utils";

registry.category("web_tour.tours").add("mail_message_load_order_tour", {
    test: true,
    steps: () => [
        {
            trigger: ".o-mail-DiscussSidebarChannel:contains(MyTestChannel)",
            run: "click",
        },
        {
            trigger: ".o-mail-Thread .o-mail-Message",
            async run() {
                await contains(".o-mail-Thread .o-mail-Message", { count: 30 });
                await contains(".o-mail-Thread", { scroll: "bottom" });
            },
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
            trigger:
                ".o-mail-Thread .o-mail-Message:first .o-mail-Message-textContent:not(:contains(31))",
            async run() {
                await contains(".o-mail-Thread .o-mail-Message", { count: 16 });
                await contains(".o-mail-Thread", { scroll: 0 });
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
                await scroll(".o-mail-Thread", "bottom");
            },
        },
        {
            // After jumping to the pinned message, the message range
            // was (1 -16): 15 before (but none were found), 15 after
            // and the pinned message itself. This trigger ensures the
            // next messages are fetched after scrolling to the bottom.
            trigger: ".o-mail-Thread .o-mail-Message .o-mail-Message-textContent:contains(17)",
            async run() {
                await contains(".o-mail-Thread .o-mail-Message", { count: 46 });
                // ensure 1 - 46  are loaded in order.
                const messages = Array.from(
                    document.querySelectorAll(".o-mail-Thread .o-mail-Message-content")
                ).map((el) => el.innerText);
                for (let i = 0; i < 46; i++) {
                    if (messages[i] !== (i + 1).toString()) {
                        throw new Error("Wrong message order after loading after");
                    }
                }
            },
        },
    ],
});
