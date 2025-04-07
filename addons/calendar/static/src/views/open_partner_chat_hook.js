import { helpers } from "@mail/core/web/open_chat_hook";
import { patch } from "@web/core/utils/patch";

patch(helpers, {
    SUPPORTED_M2X_AVATAR_MODELS: [
        ...helpers.SUPPORTED_M2X_AVATAR_MODELS,
        "res.partner",
    ],
    buildOpenChatParams(resModel, id) {
        if ("res.partner".includes(resModel)) {
            return { partnerId: id };
        }
        return super.buildOpenChatParams(...arguments);
    }
});
