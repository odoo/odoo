import {
    closeChat,
    okRating,
    feedback,
    downloadTranscript,
    confirmnClose,
} from "./website_livechat_common";
import { postMessage, waitForMessage } from "@im_livechat/../tests/tours/livechat_tour_utils";

import { registry } from "@web/core/registry";

const chatRequest = [
    ...postMessage("Hi ! What a coincidence! I need your help indeed."),
    waitForMessage("Hi ! What a coincidence! I need your help indeed."),
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
    steps: () =>
        [].concat(chatRequest, closeChat, confirmnClose, okRating, feedback, downloadTranscript),
});
