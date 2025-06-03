import { AND, fields, Record } from "./record";

export class Volume extends Record {
    static id = AND("partner_id", "guest_id");

    partner_id = fields.One("Persona");
    guest_id = fields.One("Persona");
    get persona() {
        return this.partner_id || this.guest_id;
    }
    volume = 1;
}

Volume.register();
