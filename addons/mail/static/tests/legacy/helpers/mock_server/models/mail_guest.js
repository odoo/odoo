/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/mail_guest default=false */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    _mockMailGuest__getGuestFromContext() {
        const guestId = this.pyEnv?.cookie.get("dgid");
        return guestId ? this.pyEnv["mail.guest"].searchRead([["id", "=", guestId]])[0] : null;
    },
    _mockMailGuest__initMessaging(context) {
        const channels = this._mockDiscussChannel__get_init_channels(undefined, context);
        return {
            Store: {
                hasGifPickerFeature: true,
                hasLinkPreviewFeature: true,
                initBusId: this.lastBusNotificationId,
                odoobot: this._mockResPartnerMailPartnerFormat(this.odoobotId).get(this.odoobotId),
                settings: {},
            },
            Thread: this._mockDiscussChannelChannelInfo(channels.map((channels) => channels.id)),
        };
    },
    /**
     * Simulates `_guest_format` on `mail_guest`.
     *
     * @private
     * @returns {Number[]} ids
     * @returns {Map}
     */
    _mockMailGuestGuestFormat(ids) {
        const guests = this.getRecords("mail.guest", [["id", "in", ids]], {
            active_test: false,
        });
        return new Map(
            guests.map((guest) => {
                return [
                    guest.id,
                    {
                        id: guest.id,
                        im_status: guest.im_status,
                        name: guest.name,
                        type: "guest",
                        write_date: guest.write_date,
                    },
                ];
            })
        );
    },
});
