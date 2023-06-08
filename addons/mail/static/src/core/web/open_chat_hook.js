/* @odoo-module */

import { useService } from "@web/core/utils/hooks";

export const helpers = {
    SUPPORTED_M2X_AVATAR_MODELS: ["res.users"],
    buildOpenChatParams: (resModel, id) => {
        if (resModel === "res.users") {
            return { userId: id };
        }
    },
};

export function useOpenChat(resModel) {
    const threadService = useService("mail.thread");
    if (!helpers.SUPPORTED_M2X_AVATAR_MODELS.includes(resModel)) {
        throw new Error(
            `This widget is only supported on many2one and many2many fields pointing to ${JSON.stringify(
                helpers.SUPPORTED_M2X_AVATAR_MODELS
            )}`
        );
    }
    return async (id) => {
        threadService.openChat(helpers.buildOpenChatParams(resModel, id));
    };
}
