import { fields, Record } from "@mail/model/export";

export class Volume extends Record {
    static _name = "res.users.settings.volumes";

    id;
    partner_id = fields.One("res.partner");
    guest_id = fields.One("mail.guest");
    get persona() {
        return this.partner_id || this.guest_id;
    }
    user_setting_id = fields.One("res.users.settings", { inverse: "volume_settings_ids" });
    volume = 1;
}

Volume.register();
