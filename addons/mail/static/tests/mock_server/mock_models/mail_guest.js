/** @odoo-module */

import { constants, models } from "@web/../tests/web_test_helpers";

export class MailGuest extends models.ServerModel {
    _name = "mail.guest";

    _get_guest_from_context() {
        const guestId = this.env.cookie.get("dgid");
        return guestId ? this.search_read([["id", "=", guestId]])[0] : null;
    }

    _init_messaging() {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").DiscussChannelMember} */
        const DiscussChannelMember = this.env["discuss.channel.member"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const guest = this._get_guest_from_context();
        const members = DiscussChannelMember._filter([
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
                odoobot: ResPartner.mail_partner_format(constants.ODOOBOT_ID)[constants.ODOOBOT_ID],
                self: { id: guest.id, name: guest.name, type: "guest" },
                settings: {},
            },
            Thread: DiscussChannel.channel_info(members.map((member) => member.channel_id)),
        };
    }
}
