import { chatHubService } from "@mail/core/common/chat_hub";
import { patch } from "@web/core/utils/patch";

patch(chatHubService, {
    // When LiveChat is active, chat hub is added to the live chat root
    // component, see: livechat_root.js, boot_service.js.
    start() {},
});
