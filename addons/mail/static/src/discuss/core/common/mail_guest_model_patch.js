import { MailGuest } from "@mail/core/common/mail_guest_model";
import { fields, patchModel } from "@mail/model/export";

export const mailGuestPatch = patchModel(MailGuest, {
    setup() {
        super.setup();
        this.channelMembers = fields.Many("discuss.channel.member");
    },
});
