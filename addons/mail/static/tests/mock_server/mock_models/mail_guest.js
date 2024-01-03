/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";

export class MailGuest extends models.ServerModel {
    _name = "mail.guest";

    /**
     * Simulates `_get_guest_from_context` on `mail.guest`.
     */
    _getGuestFromContext() {
        const guestId = this.env.cookie.get("dgid");
        return guestId ? this.search_read([["id", "=", guestId]])[0] : null;
    }

    /**
     * Simulates `_init_messaging` on `mail.guest`.
     */
    _initMessaging() {
        const guest = this._getGuestFromContext();
        const members = this.env["discuss.channel.member"]._filter([
            ["guest_id", "=", guest.id],
            "|",
            ["fold_state", "in", ["open", "folded"]],
            ["inviting_partner_ids", "!=", false],
        ]);
        return {
            Store: {
                current_user_id: false,
                hasGifPickerFeature: true,
                hasLinkPreviewFeature: true,
                initBusId: this.lastBusNotificationId,
                menu_id: false,
                odoobot: this.env["res.partner"].mail_partner_format(session.odoobot_id)[
                    session.odoobot_id
                ],
                self: { id: guest.id, name: guest.name, type: "guest" },
                settings: {},
            },
            Thread: this.env["discuss.channel"].channel_info(
                members.map((member) => member.channel_id)
            ),
        };
    }
}
