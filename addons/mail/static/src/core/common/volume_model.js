import { fields, Record } from "./record";

export class Volume extends Record {
    static id = "persona";

    persona = fields.One("Persona");
    volume = 1;
}

Volume.register();
