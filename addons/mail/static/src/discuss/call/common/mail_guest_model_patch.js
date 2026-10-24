import { MailGuest } from "@mail/core/common/mail_guest_model";
import { patchModel } from "@mail/model/export";
import { fields } from "@mail/model/misc";

export const mailGuestPatch = patchModel(MailGuest, {
    setup() {
        super.setup(...arguments);
        this.currentRtcSession = fields.One("discuss.channel.rtc.session", { inverse: "guest_id" });
    },
});
