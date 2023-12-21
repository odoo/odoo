/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { LivechatService } from "../common/livechat_service";

patch(LivechatService.prototype, {
    leaveSession() {
        this.busService.deleteChannel(`mail.guest_${this.guestToken}`);
        return super.leaveSession(...arguments);
    },
});
