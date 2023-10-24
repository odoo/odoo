/* @odoo-module */

import { Command } from "@mail/../tests/helpers/command";

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * Simulates `_find_or_create_for_channel` on `mail.guest`.
     */
    _mockMailGuest__findOrCreateForChannel(channelId, guestName) {
        const guestId =
            this._mockMailGuest__getGuestFromContext()?.id ??
            this.pyEnv["mail.guest"].create({ name: guestName });
        this.pyEnv["discuss.channel"].write([channelId], {
            channel_member_ids: [Command.create({ guest_id: guestId })],
        });
        return guestId;
    },
    /**
     * Simulates `_set_auth_cookie` on `mail.guest`.
     */
    _mockMailGuest__setAuthCookie(guestId) {
        this.pyEnv.cookie.set("dgid", guestId);
    },
});
