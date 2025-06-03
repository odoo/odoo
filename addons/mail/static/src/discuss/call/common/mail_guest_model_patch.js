import { MailGuest } from "@mail/core/common/mail_guest_model";
import { fields } from "@mail/model/misc";
import { patch } from "@web/core/utils/patch";

patch(MailGuest.prototype, {
    setup() {
        super.setup(...arguments);
        this.currentRtcSession = fields.One("discuss.channel.rtc.session", { inverse: "guest_id" });
    },
});
