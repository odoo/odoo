/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";

patch(Message, {
    SHADOW_LINK_COLOR: "#017e84",
    SHADOW_LINK_HOVER_COLOR: "#016b70",
});
