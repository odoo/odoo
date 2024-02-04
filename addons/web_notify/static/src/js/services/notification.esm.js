/** @odoo-module */
import {Notification} from "@web/core/notifications/notification";
import {patch} from "web.utils";

patch(Notification.props, "webNotifyProps", {
    type: {
        type: String,
        optional: true,
        validate: (t) =>
            ["warning", "danger", "success", "info", "default"].includes(t),
    },
});
