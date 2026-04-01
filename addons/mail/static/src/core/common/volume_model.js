import { OR, fields, Record } from "./record";

export class Volume extends Record {
    static id = OR("partner_id", "guest_id");

    partner_id = fields.One("res.partner");
    guest_id = fields.One("mail.guest");
    get persona() {
        return this.partner_id || this.guest_id;
    }
    volume = 1;
}

Volume.register();
