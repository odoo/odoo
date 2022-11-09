/** @odoo-module **/

import { helpers } from "@mail/views/open_chat_hook";
import { patch } from "@web/core/utils/patch";

patch(helpers, "hr_m2x_avatar_employee", {
    SUPPORTED_M2X_AVATAR_MODELS: [...helpers.SUPPORTED_M2X_AVATAR_MODELS, "hr.employee", "hr.employee.public"],
    buildOpenChatParams: function (resModel, id) {
        if (["hr.employee", "hr.employee.public"].includes(resModel)) {
            return { employeeId: id };
        }
        return this._super(...arguments);
    },
});
