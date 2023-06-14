/* @odoo-module */

import { openChat } from "../common/thread_service";

export const helpers = {
    SUPPORTED_M2X_AVATAR_MODELS: ["res.users"],
    buildOpenChatParams: (resModel, id) => {
        if (resModel === "res.users") {
            return { userId: id };
        }
    },
};

export function useOpenChat(resModel) {
    if (!helpers.SUPPORTED_M2X_AVATAR_MODELS.includes(resModel)) {
        throw new Error(
            `This widget is only supported on many2one and many2many fields pointing to ${JSON.stringify(
                helpers.SUPPORTED_M2X_AVATAR_MODELS
            )}`
        );
    }
    return async (id) => {
        openChat(helpers.buildOpenChatParams(resModel, id));
    };
}
