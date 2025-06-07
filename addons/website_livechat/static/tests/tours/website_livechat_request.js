import { queryAll } from "@odoo/hoot-dom";
import {
    closeChat,
    okRating,
    feedback,
    transcript,
    confirmnClose,
} from "./website_livechat_common";
import { registry } from "@web/core/registry";

const chatRequest = [
    {
        content: "Answer the chat request!",
        trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
        run: "edit Hi ! What a coincidence! I need your help indeed.",
    },
    {
        content: "Send the message",
        trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
        run: "press Enter",
    },
    {
        content: "Verify your message has been typed",
        trigger:
            ".o-livechat-root:shadow .o-mail-Message:contains('Hi ! What a coincidence! I need your help indeed.')",
        run: "click",
    },
    {
        content: "Verify there is no duplicates",
        trigger: ".o-livechat-root:shadow .o-mail-Thread",
        run() {
            if (
                queryAll(
                    ".o-mail-Message:contains('Hi ! What a coincidence! I need your help indeed.')",
                    { root: this.anchor }
                ).length === 1
            ) {
                document.body.classList.add("no_duplicated_message");
            }
        },
    },
    {
        content: "Is your message correctly sent ?",
        trigger: "body.no_duplicated_message",
    },
];

registry.category("web_tour.tours").add("website_livechat_chat_request_part_1_no_close_tour", {
    url: "/",
    steps: () => [].concat(chatRequest),
});

registry.category("web_tour.tours").add("website_livechat_chat_request_part_2_end_session_tour", {
    url: "/",
    steps: () => [].concat(closeChat, confirmnClose, okRating, feedback, transcript),
});
