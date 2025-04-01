import { chatHubService } from "@mail/core/common/chat_hub";
import { patch } from "@web/core/utils/patch";

patch(chatHubService, {
    // When Chatter is loaded in portal environment chat hub is added to
    // the chatter root component, see: portal_chatter.js
    start() {},
});
