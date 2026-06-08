import { mailModels } from "@mail/../tests/mail_test_helpers";

export class MailMessage extends mailModels.MailMessage {
    _store_partner_name_dynamic_fields(partnerRes) {
        super._store_partner_name_dynamic_fields(partnerRes);
        const message = this[0];
        if (message?.model !== "discuss.channel") {
            return;
        }
        const [channel] = this.env["discuss.channel"].browse(message.res_id);
        if (channel?.channel_type === "livechat") {
            partnerRes._fields = partnerRes._fields.filter((f) => f !== "name"); // mock: partner_res.remove("name")
            partnerRes.from_method("_store_livechat_username_fields");
        }
    }
}
