import { helpers } from "@mail/core/web/open_chat_hook";
import { patch } from "@web/core/utils/patch";

patch(helpers, {
    SUPPORTED_M2X_AVATAR_MODELS: [
        ...helpers.SUPPORTED_M2X_AVATAR_MODELS,
        "ai.composer",
    ],
    buildOpenChatParams(resModel, id) {
        if (["ai.composer"].includes(resModel)) {
            return { aiModelId: id };
        }
        return super.buildOpenChatParams(...arguments);
    }
});
