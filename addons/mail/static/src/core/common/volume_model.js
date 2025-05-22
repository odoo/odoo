import { fields, Record } from "./record";

export class Volume extends Record {
    static id = "persona";

    persona = fields.One("res.partner");
    volume = 1;
}

Volume.register();
