import { ChatHubPlugin } from "@mail/core/common/chat_hub";
import { patch } from "@web/core/utils/patch";

patch(ChatHubPlugin.prototype, {
    // Chathub should not be started in portal chatter
    setup() {},
});
