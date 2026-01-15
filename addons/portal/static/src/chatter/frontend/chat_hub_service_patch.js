import { chatHubService } from "@mail/core/common/chat_hub";
import { patch } from "@web/core/utils/patch";

patch(chatHubService, {
    // Chathub should not be started in portal chatter
    start() {},
});
