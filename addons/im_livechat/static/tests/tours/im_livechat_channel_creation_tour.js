import {
    clickSend,
    editComposer,
    waitForMessage,
} from "@im_livechat/../tests/tours/livechat_tour_utils";

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
        editComposer("Hello, I need help please !"),
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer button[title='Add Emojis']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-EmojiPicker .o-Emoji:contains('😀')",
            run: "click",
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-Composer-html:text('Hello, I need help please !😀')",
        },
        clickSend(),
        waitForMessage("Hello, I need help please !😀"),
    ],
});
