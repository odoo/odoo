/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    _mockMailGuest__getGuestFromContext() {
        const guestId = this.pyEnv?.cookie.get("dgid");
        return guestId ? this.pyEnv["mail.guest"].searchRead([["id", "=", guestId]])[0] : null;
    },
    _mockMailGuest__initMessaging() {
        const guest = this._mockMailGuest__getGuestFromContext();
        return {
            channels: this._mockDiscussChannelChannelInfo(guest.channel_ids),
            currentGuest: {
                id: guest.id,
                name: guest.name,
                type: "guest",
            },
            current_partner: false,
            current_user_id: false,
            current_user_settings: {},
            hasGifPickerFeature: true,
            hasLinkPreviewFeature: true,
            initBusId: this.lastBusNotificationId,
            menu_id: false,
            needaction_inbox_counter: false,
            odoobot: this._mockResPartnerMailPartnerFormat(this.odoobotId).get(this.odoobotId),
            shortcodes: [],
            starred_counter: false,
        };
    },
});
