import { MailGuest } from "@mail/core/common/mail_guest_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").MailGuest} */
const mailGuestPatch = {
    setup() {
        super.setup();
        this.channelMembers = fields.Many("discuss.channel.member");
    },
};
patch(MailGuest.prototype, mailGuestPatch);
