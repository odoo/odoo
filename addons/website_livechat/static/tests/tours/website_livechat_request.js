import {
    closeChat,
    okRating,
    feedback,
    downloadTranscript,
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
        run({ queryAll }) {
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

registry.category("web_tour.tours").add("website_livechat_chat_request", {
    url: "/",
    steps: () =>
        [].concat(chatRequest, closeChat, confirmnClose, okRating, feedback, downloadTranscript),
});
