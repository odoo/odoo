/** @odoo-module **/

import { helpers } from "@mail/core/web/open_chat_hook";
import { patch } from "@web/core/utils/patch";

patch(helpers, {
    SUPPORTED_M2X_AVATAR_MODELS: [
        ...helpers.SUPPORTED_M2X_AVATAR_MODELS,
        "hr.employee",
        "hr.employee.public",
        "hr.candidate",
    ],
    buildOpenChatParams(resModel, id) {
        if (resModel === "hr.candidate") {
            return;
        } else if (["hr.employee", "hr.employee.public"].includes(resModel)) {
            return { employeeId: id };
        }
        return super.buildOpenChatParams(...arguments);
    },
});
